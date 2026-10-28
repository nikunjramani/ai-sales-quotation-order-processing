"""Portal routes for a business's connections (ADR 0018, phase 1).

GET  /api/v1/tenants/{t}/connections[?purpose=...]
  Administrators: every connection (with last_error). Approvers: the active manager-approval
  connections they can link (P1-Q8). Others: 403. Never config, secrets or token hashes.
POST /api/v1/tenants/{t}/connections/{connection_id}/enrollments
  An approver starts linking their own account on that connection: a one-time code that works
  only there. 404 unknown (or another business's); 422 not an active approval connection.
Hosted chat (website chat, phase 4), administrators only:
POST /connections/hosted-chat {provider_key}       enable with one click (or return the
                                                   active one); gives chat_link and snippet
PATCH /connections/{id}/chat {allowed_origins?, greeting?}
PUT  /connections/{id}/chat/address {handle}      change the address once (409 if taken)
PUT  /connections/{id}/chat/active {active}       switch the chat off or on
Other tools are enabled, disabled and tested in phase 5.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from quotation_app.api.auth import PortalAuth
from quotation_app.application.channel_actions import ChannelActionService, ConnectionNotFound
from quotation_app.application.connections import (
    ConnectionService,
    ConnectionView,
    HandleTaken,
)
from quotation_app.domain.connections import Connection, ConnectionStatus, Purpose
from quotation_app.domain.tenancy import PermissionDenied, TenantContext


class ConnectionOut(BaseModel):
    connection_id: UUID
    provider_key: str
    provider_name: str
    display_name: str
    purposes: list[Purpose]
    status: ConnectionStatus
    last_error: str | None  # administrators only
    created_at: datetime
    # Hosted chat only (administrators): the public address and how to embed it.
    chat: "HostedChatOut | None" = None


class HostedChatOut(BaseModel):
    handle: str
    chat_link: str
    snippet: str
    allowed_origins: list[str]
    greeting: str
    address_changed: bool  # the address can be changed once


class EnableChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_key: str = Field(min_length=1, max_length=32)


class ChatSettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_origins: list[Annotated[str, Field(max_length=200)]] | None = Field(
        default=None, max_length=10
    )
    greeting: str | None = Field(default=None, max_length=300)


class ChatAddressIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    handle: str = Field(min_length=3, max_length=64)


class ChatActiveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool


class ConnectionEnrollmentOut(BaseModel):
    connection_id: UUID
    channel: str
    code: str
    expires_at: datetime


def hosted_chat(row: Connection, base_url: str) -> HostedChatOut | None:
    if row.public_handle is None:
        return None
    origins = row.config.get("allowed_origins", [])
    return HostedChatOut(
        handle=row.public_handle,
        chat_link=f"{base_url}/chat/{row.public_handle}",
        snippet=(
            f'<script src="{base_url}/chat/widget.js" data-chat="{row.public_handle}" '
            "async></script>"
        ),
        allowed_origins=[str(item) for item in origins] if isinstance(origins, list) else [],
        greeting=str(row.config.get("greeting") or ""),
        address_changed=row.public_handle_changed,
    )


def _view(item: ConnectionView, base_url: str) -> ConnectionOut:
    row = item.connection
    return ConnectionOut(
        connection_id=row.connection_id,
        provider_key=row.provider_key,
        provider_name=item.provider_name,
        display_name=row.display_name,
        purposes=sorted(row.purposes),
        status=row.status,
        last_error=row.last_error if item.show_errors else None,
        created_at=row.created_at,
        chat=hosted_chat(row, base_url) if item.show_errors else None,
    )


def build_connection_router(
    auth: PortalAuth,
    connections: ConnectionService,
    channels: ChannelActionService,
    base_url: str,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/tenants/{tenant_id}", tags=["portal connections"])
    Context = Annotated[TenantContext, Depends(auth.tenant_context())]

    def guarded[T](action: Callable[[], T]) -> T:
        try:
            return action()
        except PermissionDenied as error:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(error) or "Not permitted") from None
        except ConnectionNotFound:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found") from None
        except HandleTaken as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
        except SQLAlchemyError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Try again later") from None

    @router.get("/connections", response_model=list[ConnectionOut])
    def list_connections(
        context: Context, purpose: Annotated[Purpose | None, Query()] = None
    ) -> list[ConnectionOut]:
        return [
            _view(item, base_url) for item in guarded(lambda: connections.list(context, purpose))
        ]

    def admin_view(row: Connection) -> ConnectionOut:
        return _view(ConnectionView(row, connections.provider_name(row), True), base_url)

    @router.post(
        "/connections/hosted-chat", response_model=ConnectionOut, responses={403: {}, 422: {}}
    )
    def enable_chat(body: EnableChatIn, context: Context) -> ConnectionOut:
        return admin_view(
            guarded(lambda: connections.enable_hosted_chat(context, body.provider_key))
        )

    @router.patch(
        "/connections/{connection_id}/chat",
        response_model=ConnectionOut,
        responses={403: {}, 404: {}, 422: {}},
    )
    def configure_chat(
        connection_id: UUID, body: ChatSettingsIn, context: Context
    ) -> ConnectionOut:
        return admin_view(
            guarded(
                lambda: connections.configure_hosted_chat(
                    context, connection_id, body.allowed_origins, body.greeting
                )
            )
        )

    @router.put(
        "/connections/{connection_id}/chat/address",
        response_model=ConnectionOut,
        responses={403: {}, 404: {}, 409: {}, 422: {}},
    )
    def change_address(connection_id: UUID, body: ChatAddressIn, context: Context) -> ConnectionOut:
        return admin_view(
            guarded(lambda: connections.change_chat_address(context, connection_id, body.handle))
        )

    @router.put(
        "/connections/{connection_id}/chat/active",
        response_model=ConnectionOut,
        responses={403: {}, 404: {}},
    )
    def chat_active(connection_id: UUID, body: ChatActiveIn, context: Context) -> ConnectionOut:
        return admin_view(
            guarded(lambda: connections.set_hosted_chat_active(context, connection_id, body.active))
        )

    @router.post(
        "/connections/{connection_id}/enrollments",
        response_model=ConnectionEnrollmentOut,
        status_code=status.HTTP_201_CREATED,
        responses={403: {}, 404: {}, 422: {}},
    )
    def enroll(connection_id: UUID, context: Context) -> ConnectionEnrollmentOut:
        new = guarded(lambda: channels.start_enrollment(context, "", connection_id))
        return ConnectionEnrollmentOut(
            connection_id=connection_id,
            channel=new.provider_key,
            code=new.code,
            expires_at=new.expires_at,
        )

    return router
