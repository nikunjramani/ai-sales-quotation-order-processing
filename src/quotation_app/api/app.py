"""Application factory. Startup does not mutate or migrate the database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Literal

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from quotation_app.adapters.accounts.password import Argon2PasswordHasher, load_common_passwords
from quotation_app.adapters.documents.logo import PillowLogoNormalizer
from quotation_app.adapters.documents.pdf import ReportLabQuotationRenderer
from quotation_app.adapters.identity.dev import DevIdentityProvider
from quotation_app.adapters.storage.local import LocalObjectStorage
from quotation_app.api.accounts import build_account_router
from quotation_app.api.auth import PortalAuth, SessionView, build_auth_router
from quotation_app.api.business import build_business_router
from quotation_app.api.channels import build_channel_router
from quotation_app.api.connections import build_connection_router
from quotation_app.api.enquiries import build_enquiry_router
from quotation_app.api.hooks import build_hook_router
from quotation_app.api.portal import build_portal_router
from quotation_app.application.acceptance import QuotationResponseService
from quotation_app.application.accounts import (
    ApiKeyAdminService,
    BusinessService,
    InvitationService,
    LoginService,
    MemberService,
    ProfileService,
    SignupService,
)
from quotation_app.application.api_keys import ApiKeyAuthenticator
from quotation_app.application.approvals import ApprovalService
from quotation_app.application.channel_actions import ChannelActionService
from quotation_app.application.connections import ConnectionService
from quotation_app.application.documents import QuotationDocumentService
from quotation_app.application.inbound import InboundService, ManagerActionRoute
from quotation_app.application.intake import EnquiryIntakeService, EnquiryListService
from quotation_app.application.pricing import QuotationPricingService
from quotation_app.application.quotations import QuotationService
from quotation_app.application.sessions import SessionService
from quotation_app.application.tenancy import TenantContextResolver
from quotation_app.composition import build_catalogue, build_runtime
from quotation_app.config import Settings
from quotation_app.persistence.acceptance import SqlResponseStore
from quotation_app.persistence.accounts import (
    SqlBusinessStore,
    SqlInvitationStore,
    SqlMemberStore,
    SqlUserStore,
)
from quotation_app.persistence.api_keys import SqlApiKeyAdminStore, SqlApiKeyReader
from quotation_app.persistence.channels import SqlChannelStore
from quotation_app.persistence.connections import SqlConnectionStore, SqlHookLookup
from quotation_app.persistence.database import build_engine, database_ready
from quotation_app.persistence.documents import SqlDocumentReader
from quotation_app.persistence.inbound import SqlInboundStore
from quotation_app.persistence.intake import SqlEnquiryListReader, SqlIntakeStore
from quotation_app.persistence.quotations import (
    SqlApprovalStore,
    SqlQuotationReader,
    SqlRevisionStore,
)
from quotation_app.persistence.rate_limits import SqlRateLimiter
from quotation_app.persistence.seed import DEMO_MEMBERSHIPS
from quotation_app.persistence.sessions import SqlSessionStore
from quotation_app.persistence.tenancy import SqlMembershipReader, SqlPricingPolicyReader


class HealthResponse(BaseModel):
    status: Literal["ok", "ready", "not_ready"]


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()
    engine = build_engine(configuration.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Sales Quotation Automation", version="0.1.0", lifespan=lifespan)

    @app.get("/health/live", response_model=HealthResponse, tags=["health"])
    def live() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/health/ready",
        response_model=HealthResponse,
        responses={503: {"model": HealthResponse}},
        tags=["health"],
    )
    def ready(response: Response) -> HealthResponse:
        try:
            available = database_ready(engine)
        except SQLAlchemyError:
            available = False
        if not available:
            response.status_code = 503
        return HealthResponse(status="ready" if available else "not_ready")

    # Composition root: wire adapters to application services. Nothing connects until used.
    storage = LocalObjectStorage(configuration.storage_dir)
    runtime = build_runtime(configuration, engine)
    connections = SqlConnectionStore(engine)
    intake = EnquiryIntakeService(SqlIntakeStore(engine), storage, connections, runtime.registry)
    # Quotation PDFs (M5): previews for staff, approved documents for staff and customers.
    documents = QuotationDocumentService(
        SqlDocumentReader(engine), storage, ReportLabQuotationRenderer()
    )
    # Each business's own product source, through its catalogue connection (ADR 0018).
    erp = build_catalogue(engine, runtime)
    pricing = QuotationPricingService(erp, SqlPricingPolicyReader(engine))
    # Customer answers (M6): accept/decline through the API, withdrawal in the portal.
    responses = QuotationResponseService(SqlResponseStore(engine), pricing)
    business_store = SqlBusinessStore(engine)
    app.include_router(
        build_enquiry_router(
            ApiKeyAuthenticator(SqlApiKeyReader(engine)),
            intake,
            documents,
            responses,
            business_store,
        )
    )

    # Portal (M4): sessions, quotations, approvals and manager channels.
    memberships = SqlMembershipReader(engine)
    resolver = TenantContextResolver(memberships)
    session_store = SqlSessionStore(engine)
    auth = PortalAuth(
        SessionService(session_store, timedelta(hours=configuration.session_hours)), resolver
    )
    users = SqlUserStore(engine)
    profiles = ProfileService(users)
    session_view = SessionView(memberships, profiles)
    dev_login = configuration.dev_login_enabled
    app.include_router(
        build_auth_router(
            auth,
            session_view,
            DevIdentityProvider(memberships) if dev_login else None,
            sorted({subject for _, subject, _ in DEMO_MEMBERSHIPS}) if dev_login else [],
            configuration.cookie_secure,
        )
    )
    # Accounts and onboarding (phase 2): sign-up, password login, businesses, members, keys.
    hasher = Argon2PasswordHasher(max_concurrent=configuration.password_hash_concurrency)
    common = load_common_passwords()
    limiter = SqlRateLimiter(engine)
    businesses = BusinessService(business_store, users, limiter, storage, PillowLogoNormalizer())
    invitations = InvitationService(SqlInvitationStore(engine), business_store, users, limiter)
    app.include_router(
        build_account_router(
            auth,
            session_view,
            SignupService(users, hasher, limiter, common),
            LoginService(users, hasher, limiter, session_store, common),
            profiles,
            invitations,
            businesses,
            configuration.cookie_secure,
            configuration.trusted_proxy_count,
        )
    )
    app.include_router(
        build_business_router(
            auth,
            businesses,
            MemberService(SqlMemberStore(engine), business_store),
            invitations,
            ApiKeyAdminService(SqlApiKeyAdminStore(engine), business_store),
            profiles,
        )
    )
    approvals = ApprovalService(SqlApprovalStore(engine), resolver)
    channels = ChannelActionService(
        SqlChannelStore(engine), approvals, connections, runtime.registry
    )
    app.include_router(
        build_portal_router(
            auth,
            QuotationService(
                SqlQuotationReader(engine),
                SqlRevisionStore(engine),
                pricing,
            ),
            approvals,
            channels,
            EnquiryListService(SqlEnquiryListReader(engine)),
            documents,
            responses,
            connections,
        )
    )
    app.include_router(
        build_connection_router(auth, ConnectionService(connections, runtime.registry), channels)
    )
    # Provider callbacks (ADR 0018): one generic route for every provider with webhooks.
    inbox = SqlInboundStore(engine)
    app.include_router(
        build_hook_router(
            InboundService(SqlHookLookup(engine), runtime.registry, runtime.secrets, inbox)
        )
    )
    # Deprecated alias for the demo page and scripts (removed in phase 4/5).
    secret = configuration.simulated_channel_secret
    app.include_router(
        build_channel_router(
            ManagerActionRoute(channels),
            connections,
            inbox,
            None if secret is None else secret.get_secret_value(),
        )
    )
    if configuration.portal_dist_dir is not None and configuration.portal_dist_dir.is_dir():
        app.mount(
            "/portal", StaticFiles(directory=configuration.portal_dist_dir, html=True), "portal"
        )
    return app
