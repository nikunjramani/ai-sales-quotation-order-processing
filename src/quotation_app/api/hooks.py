"""Generic provider callbacks (ADR 0018).

POST /api/v1/hooks/{connection_id}/{webhook_token}
  The URL names the connection and carries its secret token; the provider's own signature is
  checked on the raw body before parsing. Events are stored once and routed by a job, so the
  answer is quick:
  200 {"received": n, "duplicates": d}   stored (or already stored)
  404 "Not found"        unknown connection, wrong token, not active or no webhook support
  413 "Event too large"  401 "Invalid signature"  400 "Invalid event"
  503 "Try again later"  the database is unavailable; providers retry and dedupe makes it safe
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from quotation_app.application.inbound import EventTooLarge, HookNotFound, InboundService
from quotation_app.ports.providers import InboundRejected, InboundRequest, InvalidInbound

# Hard ceiling before reading more; each provider's own limit is checked after that.
MAX_HOOK_BYTES = 1024 * 1024


class HookReceiptOut(BaseModel):
    received: int
    duplicates: int


def build_hook_router(service: InboundService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/hooks", tags=["provider webhooks"])

    @router.post(
        "/{connection_id}/{webhook_token}",
        response_model=HookReceiptOut,
        responses={400: {}, 401: {}, 404: {}, 413: {}, 503: {}},
    )
    async def receive(connection_id: UUID, webhook_token: str, request: Request) -> HookReceiptOut:
        declared = request.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > MAX_HOOK_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Event too large")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_HOOK_BYTES:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Event too large")
        inbound = InboundRequest(
            headers={name.lower(): value for name, value in request.headers.items()},
            body=bytes(body),
            query=dict(request.query_params),
            received_at=datetime.now(UTC),
        )
        try:
            # Database and secret-store calls block; keep them off the event loop.
            receipt = await run_in_threadpool(
                service.receive, connection_id, webhook_token, inbound
            )
        except HookNotFound:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found") from None
        except EventTooLarge:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Event too large") from None
        except InboundRejected:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature") from None
        except InvalidInbound:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid event") from None
        except SQLAlchemyError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Try again later") from None
        return HookReceiptOut(received=receipt.received, duplicates=receipt.duplicates)

    return router
