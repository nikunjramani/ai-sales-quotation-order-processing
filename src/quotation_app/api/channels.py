"""Inbound webhook for the simulated manager channel.

POST /api/v1/channels/simulated/events
  Header X-Simulated-Signature: hex HMAC-SHA256 of the raw body with the shared secret.
  Body: {"event_id", "tenant_id", "connection_id", "external_user_id", "type": "enroll"|"decision",
         "code"?, "action_reference"?, "action"?, "reason"?}

The signature is checked on the raw bytes before anything is parsed. Then the event goes to the
same ChannelActionService (and ApprovalService) a real provider adapter will use. Rejections
share one generic message so callers learn nothing about which check failed.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from quotation_app.adapters.channels.simulated import SIGNATURE_HEADER, signature_valid
from quotation_app.application.approvals import DecisionResult
from quotation_app.application.channel_actions import (
    ChannelActionRejected,
    ChannelActionService,
    ChannelEvent,
    ChannelEventKind,
)
from quotation_app.domain.quotations import (
    ApprovalAction,
    ApprovalChannel,
    DecisionConflict,
    StaleVersion,
    TaskNotFound,
)
from quotation_app.domain.tenancy import AuthorizationError

MAX_EVENT_BYTES = 16 * 1024
_REJECTED = "Action not accepted"


class SimulatedEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=200)
    tenant_id: UUID
    connection_id: str = Field(min_length=1, max_length=100)
    external_user_id: str = Field(min_length=1, max_length=200)
    type: Literal["enroll", "decision"]
    code: str | None = Field(default=None, max_length=50)
    action_reference: str | None = Field(default=None, max_length=200)
    action: ApprovalAction | None = None
    reason: str | None = Field(default=None, max_length=1000)


class SimulatedEventOut(BaseModel):
    result: Literal["enrolled", "recorded", "replayed"]
    binding_id: UUID | None = None
    decision_id: UUID | None = None
    action: ApprovalAction | None = None


def build_channel_router(service: ChannelActionService, secret: str | None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/channels", tags=["manager channels"])

    @router.post(
        "/simulated/events",
        response_model=SimulatedEventOut,
        responses={401: {}, 403: {}, 404: {}, 409: {}, 413: {}},
    )
    async def simulated_event(request: Request) -> SimulatedEventOut:
        if secret is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
        body = await request.body()
        if len(body) > MAX_EVENT_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Event too large")
        if not signature_valid(secret, body, request.headers.get(SIGNATURE_HEADER)):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")
        try:
            event = SimulatedEventIn.model_validate_json(body)
        except ValidationError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid event") from None
        try:
            # The service uses blocking database calls; keep them off the event loop.
            result = await run_in_threadpool(
                service.handle,
                ChannelEvent(
                    channel=ApprovalChannel.SIMULATED.value,
                    connection_id=event.connection_id,
                    tenant_id=event.tenant_id,
                    event_id=event.event_id,
                    external_user_id=event.external_user_id,
                    kind=ChannelEventKind(event.type),
                    code=event.code,
                    reference=event.action_reference,
                    action=event.action,
                    reason=event.reason,
                ),
            )
        except (ChannelActionRejected, AuthorizationError, TaskNotFound):
            raise HTTPException(status.HTTP_403_FORBIDDEN, _REJECTED) from None
        except (DecisionConflict, StaleVersion, IntegrityError):
            raise HTTPException(status.HTTP_409_CONFLICT, "Already decided") from None
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
        except SQLAlchemyError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Try again later") from None
        if isinstance(result, DecisionResult):
            return SimulatedEventOut(
                result="replayed" if result.replayed else "recorded",
                decision_id=result.decision.decision_id,
                action=result.decision.action,
            )
        return SimulatedEventOut(result="enrolled", binding_id=result.binding_id)

    return router
