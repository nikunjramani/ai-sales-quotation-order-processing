"""Portal routes for a business's connections (ADR 0018, phase 1).

GET  /api/v1/tenants/{t}/connections[?purpose=...]
  Administrators: every connection (with last_error). Approvers: the active manager-approval
  connections they can link (P1-Q8). Others: 403. Never config, secrets or token hashes.
POST /api/v1/tenants/{t}/connections/{connection_id}/enrollments
  An approver starts linking their own account on that connection: a one-time code that works
  only there. 404 unknown (or another business's); 422 not an active approval connection.
Enabling, disabling and testing tools come in phase 5.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from quotation_app.api.auth import PortalAuth
from quotation_app.application.channel_actions import ChannelActionService, ConnectionNotFound
from quotation_app.application.connections import ConnectionService, ConnectionView
from quotation_app.domain.connections import ConnectionStatus, Purpose
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


class ConnectionEnrollmentOut(BaseModel):
    connection_id: UUID
    channel: str
    code: str
    expires_at: datetime


def _view(item: ConnectionView) -> ConnectionOut:
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
    )


def build_connection_router(
    auth: PortalAuth, connections: ConnectionService, channels: ChannelActionService
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
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
        except SQLAlchemyError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Try again later") from None

    @router.get("/connections", response_model=list[ConnectionOut])
    def list_connections(
        context: Context, purpose: Annotated[Purpose | None, Query()] = None
    ) -> list[ConnectionOut]:
        return [_view(item) for item in guarded(lambda: connections.list(context, purpose))]

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
