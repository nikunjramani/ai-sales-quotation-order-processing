"""Contracts for durable enquiry receipt, status reads and worker-side preparation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from quotation_app.domain.attachments import AttachmentStatus
from quotation_app.domain.intake import Channel, EnquiryStatus, InboundEnvelope


class IdempotencyConflict(Exception):
    """The idempotency key was already used for a different payload."""


@dataclass(frozen=True)
class Receipt:
    enquiry_id: UUID
    status: EnquiryStatus
    payload_sha256: str
    correlation_id: UUID
    received_at: datetime


@dataclass(frozen=True)
class AttachmentView:
    attachment_id: UUID
    filename: str
    declared_content_type: str
    size_bytes: int
    status: AttachmentStatus
    rejection_reason: str | None


@dataclass(frozen=True)
class ExtractedLineView:
    sku: str
    quantity: str
    unit: str


@dataclass(frozen=True)
class ExtractionView:
    """Latest workflow result: requested lines ready for pricing, or what is still needed."""

    outcome: str
    lines: tuple[ExtractedLineView, ...]
    questions: tuple[str, ...]
    review_reasons: tuple[str, ...]


@dataclass(frozen=True)
class EnquiryView:
    enquiry_id: UUID
    channel: Channel
    status: EnquiryStatus
    customer_reference: str | None
    received_at: datetime
    correlation_id: UUID
    attachments: tuple[AttachmentView, ...]
    extraction: ExtractionView | None = None


class IntakeStore(Protocol):
    def find_receipt(
        self, tenant_id: UUID, channel: Channel, connection_id: str, provider_event_id: str
    ) -> Receipt | None: ...

    def record(
        self, envelope: InboundEnvelope, payload_sha256: str, enquiry_id: UUID
    ) -> tuple[Receipt, bool]:
        """Atomically store inbox event, enquiry, attachments and a preparation job.

        Returns (receipt, created). If another request already recorded the same provider event,
        nothing is written and the existing receipt is returned with created=False.
        """
        ...

    def get_enquiry(self, tenant_id: UUID, enquiry_id: UUID) -> EnquiryView | None: ...


@dataclass(frozen=True)
class StoredAttachment:
    attachment_id: UUID
    declared_content_type: str
    status: AttachmentStatus


class PreparationStore(Protocol):
    """Worker-side access. Every call is scoped to the job's tenant."""

    def attachments_for(self, tenant_id: UUID, enquiry_id: UUID) -> list[StoredAttachment] | None:
        """None if the enquiry does not exist for this tenant."""
        ...

    def mark_attachment(
        self,
        tenant_id: UUID,
        attachment_id: UUID,
        status: AttachmentStatus,
        detected_content_type: str | None,
        reason: str | None,
        storage_key: str,
    ) -> None: ...

    def finish_preparation(
        self, tenant_id: UUID, enquiry_id: UUID, status: EnquiryStatus, correlation_id: UUID
    ) -> None:
        """Set the enquiry status; if READY_FOR_EXTRACTION, queue the extraction job in the
        same transaction so the next step can never be lost."""
        ...
