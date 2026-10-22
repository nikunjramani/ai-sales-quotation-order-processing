"""Durable intake records (API runtime role) and preparation updates (worker role)."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert

from quotation_app.domain.attachments import AttachmentStatus
from quotation_app.domain.intake import Channel, EnquiryStatus, InboundEnvelope
from quotation_app.domain.jobs import JobKind, JobStatus
from quotation_app.persistence.models import Attachment, Enquiry, InboxEvent, Job, WorkflowRun
from quotation_app.persistence.tenancy import tenant_transaction
from quotation_app.ports.intake import (
    AttachmentView,
    EnquiryView,
    ExtractedLineView,
    ExtractionView,
    Receipt,
    StoredAttachment,
)

MAX_JOB_ATTEMPTS = 5


def _receipt(
    connection: Connection,
    tenant_id: UUID,
    channel: Channel,
    connection_id: str,
    provider_event_id: str,
) -> Receipt | None:
    row = connection.execute(
        select(
            Enquiry.id,
            Enquiry.status,
            InboxEvent.payload_sha256,
            InboxEvent.correlation_id,
            InboxEvent.received_at,
        )
        .join(Enquiry, Enquiry.inbox_event_id == InboxEvent.id)
        .where(
            InboxEvent.tenant_id == tenant_id,
            InboxEvent.channel == channel.value,
            InboxEvent.connection_id == connection_id,
            InboxEvent.provider_event_id == provider_event_id,
        )
    ).one_or_none()
    if row is None:
        return None
    return Receipt(
        enquiry_id=row.id,
        status=EnquiryStatus(row.status),
        payload_sha256=row.payload_sha256,
        correlation_id=row.correlation_id,
        received_at=row.received_at,
    )


class SqlIntakeStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_receipt(
        self, tenant_id: UUID, channel: Channel, connection_id: str, provider_event_id: str
    ) -> Receipt | None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            return _receipt(connection, tenant_id, channel, connection_id, provider_event_id)

    def record(
        self, envelope: InboundEnvelope, payload_sha256: str, enquiry_id: UUID
    ) -> tuple[Receipt, bool]:
        tenant_id = envelope.tenant_id
        with tenant_transaction(self._engine, tenant_id) as connection:
            # If a concurrent request holds the same key, PostgreSQL waits for it to finish;
            # DO NOTHING then returns no row and we read the winner's receipt instead.
            inserted = connection.execute(
                insert(InboxEvent)
                .values(
                    id=envelope.event_id,
                    tenant_id=tenant_id,
                    channel=envelope.channel.value,
                    connection_id=envelope.connection_id,
                    provider_event_id=envelope.provider_event_id,
                    payload_sha256=payload_sha256,
                    envelope=envelope.to_json(),
                    received_at=envelope.received_at,
                    correlation_id=envelope.correlation_id,
                )
                .on_conflict_do_nothing(
                    index_elements=["tenant_id", "channel", "connection_id", "provider_event_id"]
                )
                .returning(InboxEvent.id)
            ).scalar_one_or_none()
            if inserted is None:
                existing = _receipt(
                    connection,
                    tenant_id,
                    envelope.channel,
                    envelope.connection_id,
                    envelope.provider_event_id,
                )
                if existing is None:
                    raise RuntimeError("Conflicting inbox event is not visible")
                return existing, False

            connection.execute(
                insert(Enquiry).values(
                    id=enquiry_id,
                    tenant_id=tenant_id,
                    inbox_event_id=envelope.event_id,
                    channel=envelope.channel.value,
                    status=EnquiryStatus.RECEIVED.value,
                    customer_reference=envelope.sender_external_id,
                    text=envelope.text,
                    correlation_id=envelope.correlation_id,
                    received_at=envelope.received_at,
                )
            )
            for item in envelope.attachments:
                connection.execute(
                    insert(Attachment).values(
                        id=item.attachment_id,
                        tenant_id=tenant_id,
                        enquiry_id=enquiry_id,
                        filename=item.filename,
                        declared_content_type=item.declared_content_type,
                        size_bytes=item.size_bytes,
                        sha256=item.sha256,
                        status=AttachmentStatus.QUARANTINED.value,
                        storage_key=item.storage_key,
                    )
                )
            connection.execute(
                insert(Job).values(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    kind=JobKind.PREPARE_ENQUIRY.value,
                    payload={"enquiry_id": str(enquiry_id)},
                    status=JobStatus.PENDING.value,
                    max_attempts=MAX_JOB_ATTEMPTS,
                    run_at=func.now(),
                    correlation_id=envelope.correlation_id,
                )
            )
        receipt = Receipt(
            enquiry_id=enquiry_id,
            status=EnquiryStatus.RECEIVED,
            payload_sha256=payload_sha256,
            correlation_id=envelope.correlation_id,
            received_at=envelope.received_at,
        )
        return receipt, True

    def get_enquiry(self, tenant_id: UUID, enquiry_id: UUID) -> EnquiryView | None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            enquiry = connection.execute(
                select(
                    Enquiry.id,
                    Enquiry.channel,
                    Enquiry.status,
                    Enquiry.customer_reference,
                    Enquiry.received_at,
                    Enquiry.correlation_id,
                ).where(Enquiry.tenant_id == tenant_id, Enquiry.id == enquiry_id)
            ).one_or_none()
            if enquiry is None:
                return None
            attachments = connection.execute(
                select(
                    Attachment.id,
                    Attachment.filename,
                    Attachment.declared_content_type,
                    Attachment.size_bytes,
                    Attachment.status,
                    Attachment.rejection_reason,
                )
                .where(Attachment.tenant_id == tenant_id, Attachment.enquiry_id == enquiry_id)
                .order_by(Attachment.created_at, Attachment.id)
            ).all()
            run = connection.execute(
                select(WorkflowRun.status, WorkflowRun.outcome)
                .where(
                    WorkflowRun.tenant_id == tenant_id,
                    WorkflowRun.enquiry_id == enquiry_id,
                    WorkflowRun.outcome.is_not(None),
                )
                .order_by(WorkflowRun.updated_at.desc())
                .limit(1)
            ).one_or_none()
        return EnquiryView(
            enquiry_id=enquiry.id,
            channel=Channel(enquiry.channel),
            status=EnquiryStatus(enquiry.status),
            customer_reference=enquiry.customer_reference,
            received_at=enquiry.received_at,
            correlation_id=enquiry.correlation_id,
            attachments=tuple(
                AttachmentView(
                    attachment_id=row.id,
                    filename=row.filename,
                    declared_content_type=row.declared_content_type,
                    size_bytes=row.size_bytes,
                    status=AttachmentStatus(row.status),
                    rejection_reason=row.rejection_reason,
                )
                for row in attachments
            ),
            extraction=None if run is None else _extraction_view(run.status, run.outcome),
        )


def _extraction_view(status: str, outcome: dict[str, Any]) -> ExtractionView:
    return ExtractionView(
        outcome=status,
        lines=tuple(
            ExtractedLineView(str(line["sku"]), str(line["quantity"]), str(line["unit"]))
            for line in outcome.get("lines", [])
        ),
        questions=tuple(str(question) for question in outcome.get("questions", [])),
        review_reasons=tuple(str(reason) for reason in outcome.get("review_reasons", [])),
    )


class SqlPreparationStore:
    """Worker-role access; every method sets the job's tenant context first."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def attachments_for(self, tenant_id: UUID, enquiry_id: UUID) -> list[StoredAttachment] | None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            exists = connection.execute(
                select(Enquiry.id).where(Enquiry.tenant_id == tenant_id, Enquiry.id == enquiry_id)
            ).one_or_none()
            if exists is None:
                return None
            rows = connection.execute(
                select(Attachment.id, Attachment.declared_content_type, Attachment.status)
                .where(Attachment.tenant_id == tenant_id, Attachment.enquiry_id == enquiry_id)
                .order_by(Attachment.created_at, Attachment.id)
            ).all()
        return [
            StoredAttachment(row.id, row.declared_content_type, AttachmentStatus(row.status))
            for row in rows
        ]

    def mark_attachment(
        self,
        tenant_id: UUID,
        attachment_id: UUID,
        status: AttachmentStatus,
        detected_content_type: str | None,
        reason: str | None,
        storage_key: str,
    ) -> None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            connection.execute(
                update(Attachment)
                .where(Attachment.tenant_id == tenant_id, Attachment.id == attachment_id)
                .values(
                    status=status.value,
                    detected_content_type=detected_content_type,
                    rejection_reason=reason,
                    storage_key=storage_key,
                    updated_at=func.now(),
                )
            )

    def finish_preparation(
        self, tenant_id: UUID, enquiry_id: UUID, status: EnquiryStatus, correlation_id: UUID
    ) -> None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            # Only the first completion moves the enquiry on, so a re-run cannot queue twice.
            changed = connection.execute(
                update(Enquiry)
                .where(
                    Enquiry.tenant_id == tenant_id,
                    Enquiry.id == enquiry_id,
                    Enquiry.status == EnquiryStatus.RECEIVED.value,
                )
                .values(status=status.value, updated_at=func.now())
            ).rowcount
            if changed and status is EnquiryStatus.READY_FOR_EXTRACTION:
                connection.execute(
                    insert(Job).values(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        kind=JobKind.EXTRACT_REQUIREMENTS.value,
                        payload={"enquiry_id": str(enquiry_id)},
                        status=JobStatus.PENDING.value,
                        max_attempts=MAX_JOB_ATTEMPTS,
                        run_at=func.now(),
                        correlation_id=correlation_id,
                    )
                )
