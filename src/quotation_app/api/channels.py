"""DEPRECATED inbound route for the simulated manager phone (kept in phase 1, ADR 0018 §5.2).

POST /api/v1/channels/simulated/events
  Header X-Simulated-Signature: hex HMAC-SHA256 of the raw body with the global development
  secret (QUOTATION_SIMULATED_CHANNEL_SECRET).
  Body: {"event_id", "tenant_id", "connection_id", "external_user_id", "type": "enroll"|"decision",
         "code"?, "action_reference"?, "action"?, "reason"?}

New callers use the generic route /api/v1/hooks/{connection_id}/{token}, where the business
comes from the connection and each connection has its own secret. This alias stays because the
demo page and scripts rely on its synchronous answers (enrolled / recorded / replayed, 403,
409); it is removed when the demo moves to a real provider (phase 4/5).

It works on the new framework: the signature is checked on the raw bytes first, the body's
tenant_id and connection_id only FIND that business's active `simulated` connection (none:
403), the event is stored in inbox_events and routed in the request through the same
ChannelActionService (and ApprovalService) every provider uses. Known weakness (development
only, refused in production): the body chooses among businesses that share the dev secret.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from quotation_app.adapters.providers.simulated import PROVIDER_KEY
from quotation_app.adapters.providers.simulated.signing import SIGNATURE_HEADER, signature_valid
from quotation_app.application.approvals import DecisionResult
from quotation_app.application.channel_actions import ChannelActionRejected
from quotation_app.application.inbound import ManagerActionRoute
from quotation_app.domain.intake import ManagerAction, validate_event
from quotation_app.domain.quotations import (
    ApprovalAction,
    DecisionConflict,
    StaleVersion,
    TaskNotFound,
)
from quotation_app.domain.tenancy import AuthorizationError
from quotation_app.ports.channels import ChannelBinding
from quotation_app.ports.connections import ConnectionStore
from quotation_app.ports.inbound import InboundStore

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


def build_channel_router(
    route: ManagerActionRoute,
    connections: ConnectionStore,
    inbox: InboundStore,
    secret: str | None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/channels", tags=["manager channels (deprecated)"])

    def handle(event: SimulatedEventIn) -> ChannelBinding | DecisionResult:
        connection = connections.find_by_account(event.tenant_id, PROVIDER_KEY, event.connection_id)
        if connection is None or not connection.active:
            raise ChannelActionRejected(_REJECTED)
        action = validate_event(
            ManagerAction(
                provider_event_id=event.event_id,
                external_user_id=event.external_user_id,
                kind=event.type,
                code=event.code,
                reference=event.action_reference,
                action=event.action.value if event.action else None,
                reason=event.reason,
            )
        )
        assert isinstance(action, ManagerAction)
        [recorded] = inbox.record(connection, [action], datetime.now(UTC), queue_jobs=False)
        # A repeated event is routed again: the services are idempotent, so it says "replayed".
        result = route.handle(connection, action)
        outcome = (
            ("replayed" if result.replayed else "recorded")
            if isinstance(result, DecisionResult)
            else "enrolled"
        )
        inbox.mark_processed(connection.tenant_id, recorded.inbox_event_id, outcome)
        return result

    @router.post(
        "/simulated/events",
        response_model=SimulatedEventOut,
        responses={401: {}, 403: {}, 404: {}, 409: {}, 413: {}},
        deprecated=True,
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
            # The services use blocking database calls; keep them off the event loop.
            result = await run_in_threadpool(handle, event)
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
