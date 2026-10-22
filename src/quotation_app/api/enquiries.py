"""Versioned enquiry intake API.

POST /api/v1/enquiries  accepts an enquiry (202), or returns the original result for a replay
                        with the same Idempotency-Key (200). A different payload under a used key
                        is rejected (409). 202 is sent only after the database commit.
GET  /api/v1/enquiries/{id}  returns status. Other tenants' IDs return 404, like unknown IDs.

The tenant always comes from the API key, never from the request body.
"""

import base64
import binascii
from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from quotation_app.application.api_keys import ApiKeyAuthenticator, AuthenticationFailed
from quotation_app.application.intake import EnquiryIntakeService
from quotation_app.domain.intake import (
    MAX_ATTACHMENT_BYTES,
    MAX_ATTACHMENTS,
    MAX_TEXT_CHARACTERS,
    MAX_TOTAL_ATTACHMENT_BYTES,
    AttachmentUpload,
    EnquirySubmission,
)
from quotation_app.domain.tenancy import PermissionDenied, TenantContext
from quotation_app.ports.intake import EnquiryView, IdempotencyConflict

# Base64 is about 4/3 of the binary size; allow headroom for JSON and text.
MAX_REQUEST_BYTES = MAX_TOTAL_ATTACHMENT_BYTES * 4 // 3 + MAX_TEXT_CHARACTERS * 4 + 64 * 1024
_UNAVAILABLE = "Temporarily unavailable; retry with the same Idempotency-Key"


class AttachmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100, examples=["application/pdf"])
    content_base64: str = Field(min_length=1, max_length=MAX_ATTACHMENT_BYTES * 4 // 3 + 4)


class EnquiryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARACTERS)
    customer_reference: str | None = Field(default=None, max_length=200)
    attachments: list[AttachmentIn] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)


class EnquiryAccepted(BaseModel):
    enquiry_id: UUID
    status: str
    duplicate: bool
    correlation_id: UUID
    received_at: datetime


class AttachmentOut(BaseModel):
    attachment_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    rejection_reason: str | None


class EnquiryOut(BaseModel):
    enquiry_id: UUID
    channel: str
    status: str
    customer_reference: str | None
    received_at: datetime
    correlation_id: UUID
    attachments: list[AttachmentOut]


def _to_submission(body: EnquiryIn) -> EnquirySubmission:
    uploads = []
    for item in body.attachments:
        try:
            data = base64.b64decode(item.content_base64, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError(f"Attachment {item.filename!r} is not valid base64") from None
        uploads.append(AttachmentUpload(item.filename, item.content_type, data))
    return EnquirySubmission(body.text, body.customer_reference, tuple(uploads))


def _view(enquiry: EnquiryView) -> EnquiryOut:
    return EnquiryOut(
        enquiry_id=enquiry.enquiry_id,
        channel=enquiry.channel.value,
        status=enquiry.status.value,
        customer_reference=enquiry.customer_reference,
        received_at=enquiry.received_at,
        correlation_id=enquiry.correlation_id,
        attachments=[
            AttachmentOut(
                attachment_id=item.attachment_id,
                filename=item.filename,
                content_type=item.declared_content_type,
                size_bytes=item.size_bytes,
                status=item.status.value,
                rejection_reason=item.rejection_reason,
            )
            for item in enquiry.attachments
        ],
    )


def build_enquiry_router(
    authenticator: ApiKeyAuthenticator, intake: EnquiryIntakeService
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/enquiries", tags=["enquiries"])
    bearer = HTTPBearer(auto_error=False, description="API key: qk_<id>_<secret>")

    def authenticate(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> TenantContext:
        try:
            if credentials is None:
                raise AuthenticationFailed("Invalid credentials")
            return authenticator.authenticate(credentials.credentials)
        except AuthenticationFailed:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except SQLAlchemyError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from None

    def limit_body(request: Request) -> None:
        length = request.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_REQUEST_BYTES):
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Request too large")

    def guarded[T](action: Callable[[], T]) -> T:
        try:
            return action()
        except PermissionDenied:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted") from None
        except IdempotencyConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
        except (SQLAlchemyError, OSError):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from None

    @router.post(
        "",
        response_model=EnquiryAccepted,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(limit_body)],
        responses={
            200: {"model": EnquiryAccepted, "description": "Replay of an accepted request"},
            401: {"description": "Missing or invalid API key"},
            403: {"description": "Key lacks enquiries:submit"},
            409: {"description": "Idempotency-Key reused with a different payload"},
            413: {"description": "Request too large"},
            503: {"description": "Not stored; retry with the same Idempotency-Key"},
        },
    )
    def submit(
        body: EnquiryIn,
        response: Response,
        context: Annotated[TenantContext, Depends(authenticate)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> EnquiryAccepted:
        result = guarded(lambda: intake.submit(context, _to_submission(body), idempotency_key))
        if result.duplicate:
            response.status_code = status.HTTP_200_OK
        receipt = result.receipt
        response.headers["X-Correlation-ID"] = str(receipt.correlation_id)
        return EnquiryAccepted(
            enquiry_id=receipt.enquiry_id,
            status=receipt.status.value,
            duplicate=result.duplicate,
            correlation_id=receipt.correlation_id,
            received_at=receipt.received_at,
        )

    @router.get("/{enquiry_id}", response_model=EnquiryOut, responses={404: {}})
    def get_status(
        enquiry_id: UUID, context: Annotated[TenantContext, Depends(authenticate)]
    ) -> EnquiryOut:
        enquiry = guarded(lambda: intake.status(context, enquiry_id))
        if enquiry is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Enquiry not found")
        return _view(enquiry)

    return router
