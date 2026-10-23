"""Portal sign-in and session routes, plus the dependencies other portal routes use.

GET  /api/v1/auth/config     which sign-in method is active (and demo users for the dev login)
POST /api/v1/auth/dev-login  dev only: sign in as a stored synthetic member, sets the cookie
GET  /api/v1/auth/session    who is signed in, their tenants and the CSRF token
POST /api/v1/auth/logout     ends the session (needs the CSRF header)

The session token lives only in an HttpOnly, SameSite=Strict cookie, so page scripts cannot
read it and other sites cannot make the browser send it. Every state-changing request must
also carry the X-CSRF-Token header.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from quotation_app.adapters.identity.dev import DevIdentityProvider
from quotation_app.application.api_keys import AuthenticationFailed
from quotation_app.application.sessions import SessionService, csrf_token_for
from quotation_app.application.tenancy import TenantContextResolver
from quotation_app.domain.tenancy import AccessDenied, TenantContext
from quotation_app.ports.identity import IdentityRejected, SessionRecord
from quotation_app.ports.tenancy import MembershipDirectory

SESSION_COOKIE = "quotation_session"
CSRF_HEADER = "X-CSRF-Token"
COOKIE_PATH = "/api"
_UNAVAILABLE = "Temporarily unavailable; try again"


@dataclass(frozen=True)
class SignedIn:
    """The current person plus their raw session token (needed for the CSRF check)."""

    record: SessionRecord
    token: str


class AuthConfigOut(BaseModel):
    provider: Literal["dev", "disabled"]
    dev_subjects: list[str]


class DevLoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(min_length=3, max_length=200)


class TenantOut(BaseModel):
    tenant_id: UUID
    name: str
    roles: list[str]
    permissions: list[str]


class SessionOut(BaseModel):
    subject: str
    provider: str
    expires_at: datetime
    csrf_token: str
    tenants: list[TenantOut]


@dataclass(frozen=True)
class PortalAuth:
    """FastAPI dependencies shared by every portal router."""

    sessions: SessionService
    resolver: TenantContextResolver

    def signed_in(self) -> Callable[[Request], SignedIn]:
        def dependency(request: Request) -> SignedIn:
            token = request.cookies.get(SESSION_COOKIE)
            try:
                record = self.sessions.authenticate(token)
            except AuthenticationFailed:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in") from None
            except SQLAlchemyError:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from None
            assert token is not None
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                try:
                    self.sessions.check_csrf(token, request.headers.get(CSRF_HEADER))
                except AuthenticationFailed:
                    raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing CSRF token") from None
            return SignedIn(record, token)

        return dependency

    def tenant_context(self) -> Callable[[UUID, SignedIn], TenantContext]:
        signed_in = self.signed_in()

        def dependency(
            tenant_id: UUID, person: Annotated[SignedIn, Depends(signed_in)]
        ) -> TenantContext:
            try:
                return self.resolver.resolve(person.record.subject, tenant_id)
            except AccessDenied:
                # Same answer for "not a member" and "no such tenant".
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found") from None
            except SQLAlchemyError:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from None

        return dependency


def _set_cookie(response: Response, token: str, max_age: int, secure: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        path=COOKIE_PATH,
        httponly=True,
        secure=secure,
        samesite="strict",
    )


def build_auth_router(
    auth: PortalAuth,
    directory: MembershipDirectory,
    dev: DevIdentityProvider | None,
    dev_subjects: list[str],
    cookie_secure: bool,
) -> APIRouter:
    """dev is the development identity provider, or None when the dev login is disabled."""
    router = APIRouter(prefix="/api/v1/auth", tags=["portal auth"])
    provider: Literal["dev", "disabled"] = "dev" if dev is not None else "disabled"
    signed_in = auth.signed_in()

    def session_out(person: SignedIn) -> SessionOut:
        memberships = directory.tenants_for(person.record.subject)
        return SessionOut(
            subject=person.record.subject,
            provider=person.record.provider,
            expires_at=person.record.expires_at,
            csrf_token=csrf_token_for(person.token),
            tenants=[
                TenantOut(
                    tenant_id=item.tenant_id,
                    name=item.tenant_name,
                    roles=sorted(role.value for role in item.roles),
                    permissions=sorted(
                        permission.value
                        for permission in TenantContext(
                            item.tenant_id, person.record.subject, item.roles
                        ).permissions
                    ),
                )
                for item in memberships
            ],
        )

    @router.get("/config", response_model=AuthConfigOut)
    def config() -> AuthConfigOut:
        return AuthConfigOut(
            provider=provider, dev_subjects=dev_subjects if provider == "dev" else []
        )

    @router.post("/dev-login", response_model=SessionOut, responses={401: {}, 404: {}})
    def dev_login(body: DevLoginIn, response: Response) -> SessionOut:
        if dev is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
        try:
            identity = dev.verify(body.subject)
            new = auth.sessions.start(identity)
            record = auth.sessions.authenticate(new.token)
        except (IdentityRejected, AuthenticationFailed):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in failed") from None
        except SQLAlchemyError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from None
        _set_cookie(response, new.token, int(auth.sessions.lifetime.total_seconds()), cookie_secure)
        return session_out(SignedIn(record, new.token))

    @router.get("/session", response_model=SessionOut, responses={401: {}})
    def current(person: Annotated[SignedIn, Depends(signed_in)]) -> SessionOut:
        try:
            return session_out(person)
        except SQLAlchemyError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from None

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses={401: {}, 403: {}})
    def logout(person: Annotated[SignedIn, Depends(signed_in)], response: Response) -> None:
        auth.sessions.end(person.token)
        response.delete_cookie(
            SESSION_COOKIE, path=COOKIE_PATH, httponly=True, secure=cookie_secure, samesite="strict"
        )

    return router
