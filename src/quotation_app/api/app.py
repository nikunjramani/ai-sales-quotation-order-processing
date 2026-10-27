"""Application factory. Startup does not mutate or migrate the database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Literal

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from quotation_app.adapters.documents.pdf import ReportLabQuotationRenderer
from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.adapters.identity.dev import DevIdentityProvider
from quotation_app.adapters.storage.local import LocalObjectStorage
from quotation_app.api.auth import PortalAuth, build_auth_router
from quotation_app.api.channels import build_channel_router
from quotation_app.api.enquiries import build_enquiry_router
from quotation_app.api.hooks import build_hook_router
from quotation_app.api.portal import build_portal_router
from quotation_app.application.acceptance import QuotationResponseService
from quotation_app.application.api_keys import ApiKeyAuthenticator
from quotation_app.application.approvals import ApprovalService
from quotation_app.application.channel_actions import ChannelActionService
from quotation_app.application.documents import QuotationDocumentService
from quotation_app.application.inbound import InboundService, ManagerActionRoute
from quotation_app.application.intake import EnquiryIntakeService, EnquiryListService
from quotation_app.application.pricing import QuotationPricingService
from quotation_app.application.quotations import QuotationService
from quotation_app.application.sessions import SessionService
from quotation_app.application.tenancy import TenantContextResolver
from quotation_app.composition import build_runtime
from quotation_app.config import Settings
from quotation_app.persistence.acceptance import SqlResponseStore
from quotation_app.persistence.api_keys import SqlApiKeyReader
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
from quotation_app.persistence.seed import DEMO_MEMBERSHIPS, INDUSTRIAL_TENANT, OFFICE_TENANT
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
    runtime = build_runtime(configuration)
    connections = SqlConnectionStore(engine)
    intake = EnquiryIntakeService(SqlIntakeStore(engine), storage, connections, runtime.registry)
    # Quotation PDFs (M5): previews for staff, approved documents for staff and customers.
    documents = QuotationDocumentService(
        SqlDocumentReader(engine), storage, ReportLabQuotationRenderer()
    )
    # Only the simulated ERP exists until a pilot ERP is connected (M7).
    erp = SimulatedErp(demo_catalogues(INDUSTRIAL_TENANT, OFFICE_TENANT))
    pricing = QuotationPricingService(erp, SqlPricingPolicyReader(engine))
    # Customer answers (M6): accept/decline through the API, withdrawal in the portal.
    responses = QuotationResponseService(SqlResponseStore(engine), pricing)
    app.include_router(
        build_enquiry_router(
            ApiKeyAuthenticator(SqlApiKeyReader(engine)), intake, documents, responses
        )
    )

    # Portal (M4): sessions, quotations, approvals and manager channels.
    memberships = SqlMembershipReader(engine)
    resolver = TenantContextResolver(memberships)
    auth = PortalAuth(
        SessionService(SqlSessionStore(engine), timedelta(hours=configuration.session_hours)),
        resolver,
    )
    dev_login = configuration.portal_login == "dev"
    app.include_router(
        build_auth_router(
            auth,
            memberships,
            DevIdentityProvider(memberships) if dev_login else None,
            sorted({subject for _, subject, _ in DEMO_MEMBERSHIPS}) if dev_login else [],
            configuration.cookie_secure,
        )
    )
    approvals = ApprovalService(SqlApprovalStore(engine), resolver)
    channels = ChannelActionService(SqlChannelStore(engine), approvals)
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
        )
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
