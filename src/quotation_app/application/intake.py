"""Accept an enquiry: store it durably, deduplicate replays, queue preparation work.

The caller is told "accepted" only after the database transaction commits, so an accepted
enquiry is never lost. Attachment bytes go to quarantine storage before that transaction;
if the transaction fails or loses a duplicate race, those files are removed again.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from quotation_app.application.providers import ProviderRegistry
from quotation_app.domain.attachments import StorageArea, attachment_key
from quotation_app.domain.documents import delivery_recipient
from quotation_app.domain.intake import (
    AttachmentRecord,
    EnquiryStatus,
    EnquirySubmission,
    InboundEnvelope,
    validate_idempotency_key,
)
from quotation_app.domain.tenancy import Permission, PermissionDenied, TenantContext
from quotation_app.ports.connections import ConnectionStore
from quotation_app.ports.intake import (
    EnquiryListReader,
    EnquirySummary,
    EnquiryView,
    IdempotencyConflict,
    IntakeStore,
    Receipt,
)
from quotation_app.ports.storage import ObjectStorage


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class IntakeResult:
    receipt: Receipt
    duplicate: bool


class EnquiryIntakeService:
    def __init__(
        self,
        store: IntakeStore,
        storage: ObjectStorage,
        connections: ConnectionStore,
        registry: ProviderRegistry,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._storage = storage
        self._connections = connections
        self._registry = registry
        self._clock = clock

    def submit(
        self,
        context: TenantContext,
        submission: EnquirySubmission,
        idempotency_key: str,
        provider_key: str,
    ) -> IntakeResult:
        """Raises PermissionDenied, ValueError (invalid key) or IdempotencyConflict.

        The authenticated credential is the connection (ADR 0018): the business's connection
        of this provider whose account is the caller's subject (an API key's "api-key:<id>").
        A missing or disabled connection is refused. Two connections never share keys.
        """
        context.require(Permission.SUBMIT_ENQUIRIES)
        validate_idempotency_key(idempotency_key)
        connection = self._connections.find_by_account(
            context.tenant_id, provider_key, context.subject
        )
        provider = None if connection is None else self._registry.find(provider_key)
        if connection is None or not connection.active or provider is None:
            raise PermissionDenied("This credential cannot submit enquiries")
        fingerprint = submission.fingerprint()

        existing = self._store.find_receipt(
            context.tenant_id, connection.connection_id, idempotency_key
        )
        if existing is not None:
            return self._replay(existing, fingerprint)

        attachments = tuple(
            AttachmentRecord(
                attachment_id=attachment_id,
                filename=upload.filename,
                declared_content_type=upload.declared_content_type,
                size_bytes=len(upload.data),
                sha256=upload.sha256,
                storage_key=attachment_key(
                    context.tenant_id, attachment_id, StorageArea.QUARANTINE
                ),
            )
            for upload, attachment_id in ((upload, uuid4()) for upload in submission.attachments)
        )
        envelope = InboundEnvelope(
            event_id=uuid4(),
            tenant_id=context.tenant_id,
            channel=connection.provider_key,
            connection_id=connection.legacy_key,
            connection_ref=connection.connection_id,
            reply_to=delivery_recipient(
                provider.capabilities.delivery_mode,
                connection.legacy_key,
                submission.customer_reference,
            ),
            provider_event_id=idempotency_key,
            sender_external_id=submission.customer_reference,
            received_at=self._clock(),
            text=submission.text,
            attachments=attachments,
            correlation_id=uuid4(),
        )
        try:
            for upload, record in zip(submission.attachments, attachments, strict=True):
                self._storage.put(record.storage_key, upload.data)
            receipt, created = self._store.record(envelope, fingerprint, enquiry_id=uuid4())
        except BaseException:
            self._discard(attachments)
            raise
        if not created:
            self._discard(attachments)
            return self._replay(receipt, fingerprint)
        return IntakeResult(receipt, duplicate=False)

    def status(self, context: TenantContext, enquiry_id: UUID) -> EnquiryView | None:
        """None for unknown IDs and for other tenants' IDs alike."""
        context.require(Permission.VIEW_ENQUIRIES)
        return self._store.get_enquiry(context.tenant_id, enquiry_id)

    def _replay(self, receipt: Receipt, fingerprint: str) -> IntakeResult:
        if receipt.payload_sha256 != fingerprint:
            raise IdempotencyConflict("Idempotency-Key was already used for a different payload")
        return IntakeResult(receipt, duplicate=True)

    def _discard(self, attachments: tuple[AttachmentRecord, ...]) -> None:
        for record in attachments:
            self._storage.delete(record.storage_key)


class EnquiryListService:
    """Portal list of a tenant's enquiries, e.g. those needing review or clarification."""

    def __init__(self, reader: EnquiryListReader) -> None:
        self._reader = reader

    def list(
        self, context: TenantContext, statuses: frozenset[EnquiryStatus] | None = None
    ) -> list[EnquirySummary]:
        context.require(Permission.VIEW_ENQUIRIES)
        return self._reader.list_enquiries(context.tenant_id, statuses, 100)
