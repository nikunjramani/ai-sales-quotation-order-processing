"""Job handler: render an approved quotation's PDF (once) and deliver it to the customer.

Flow for one delivery (a row written in the same transaction as the job that processes it):
1. Already finished (available/sent/failed/unknown)? Do nothing.
2. Left in 'sending' by an earlier attempt? That worker stopped after handing the document over
   and before recording the result, so we cannot know if it arrived: mark 'unknown' for a
   person to check, never resend blindly.
3. Get the document: reuse the stored one (hash re-checked) or render it from the approved
   version and store it. Only a version with an approve decision for its exact content hash
   can be rendered.
4. Compare-and-set pending -> sending, so only one worker can hand it over.
5. Ask the channel adapter. Accepted -> available/sent. Rejected -> failed. Possibly sent
   (timeout) -> unknown. Any other error -> back to pending and retried with backoff; after the
   last attempt -> failed.
Problems that retrying cannot fix are recorded on the delivery (failed + reason) so they show
in the portal, instead of silently vanishing.
"""

import hashlib
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from uuid import UUID

from quotation_app.application.documents import read_verified
from quotation_app.domain.documents import (
    FINAL_DELIVERY_STATUSES,
    DeliveryStatus,
    DocumentIntegrityError,
    DocumentKind,
    DocumentNotAvailable,
    StoredDocument,
    UnrenderableContent,
    clean_error,
    document_filename,
    document_id,
    document_key,
)
from quotation_app.domain.jobs import PermanentJobError
from quotation_app.domain.quotations import quotation_number
from quotation_app.ports.documents import (
    DeliveryChannel,
    DeliveryRejected,
    DeliveryRequest,
    DeliveryStore,
    DeliveryUncertain,
    DeliveryWork,
    QuotationRenderer,
    ReceiptKind,
)
from quotation_app.ports.jobs import ClaimedJob
from quotation_app.ports.storage import ObjectNotFound, ObjectStorage

logger = logging.getLogger(__name__)

_PENDING = frozenset({DeliveryStatus.PENDING})
_SENDING = frozenset({DeliveryStatus.SENDING})
_INTERRUPTED = "The worker stopped while handing the document over; check with the provider"


def utc_now() -> datetime:
    return datetime.now(UTC)


class QuotationDeliveryHandler:
    def __init__(
        self,
        store: DeliveryStore,
        storage: ObjectStorage,
        renderer: QuotationRenderer,
        channels: Mapping[str, DeliveryChannel],
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._storage = storage
        self._renderer = renderer
        self._channels = dict(channels)
        self._clock = clock

    def __call__(self, job: ClaimedJob) -> None:
        try:
            delivery_id = UUID(job.payload["delivery_id"])
        except (KeyError, ValueError):
            raise PermanentJobError("Job payload has no valid delivery_id") from None
        tenant_id = job.tenant_id
        work = self._store.delivery(tenant_id, delivery_id)
        if work is None:
            raise PermanentJobError("Delivery not found")
        status = work.record.status
        if status in FINAL_DELIVERY_STATUSES:
            return
        if status is DeliveryStatus.SENDING:
            self._store.set_status(
                tenant_id,
                delivery_id,
                DeliveryStatus.UNKNOWN,
                expected=_SENDING,
                error=_INTERRUPTED,
            )
            return

        def fail(reason: str, expected: frozenset[DeliveryStatus] = _PENDING) -> None:
            logger.warning("Delivery %s failed: %s", delivery_id, reason)
            self._store.set_status(
                tenant_id,
                delivery_id,
                DeliveryStatus.FAILED,
                expected=expected,
                error=clean_error(reason),
            )

        channel = self._channels.get(work.record.channel)
        if channel is None:
            fail(f"No delivery channel is configured for '{work.record.channel}'")
            return
        try:
            document, data = self._document(tenant_id, work)
        except (DocumentNotAvailable, UnrenderableContent, DocumentIntegrityError) as error:
            fail(str(error))
            return
        except ObjectNotFound:
            fail("The stored document file is missing")
            return
        if not self._store.set_status(
            tenant_id,
            delivery_id,
            DeliveryStatus.SENDING,
            expected=_PENDING,
            document_id=document.document_id,
        ):
            return  # another worker took it over
        record = work.record
        request = DeliveryRequest(
            delivery_id=delivery_id,
            tenant_id=tenant_id,
            tenant_name=work.tenant_name,
            quotation_id=record.quotation_id,
            quotation_number=quotation_number(record.quotation_id),
            version=record.version,
            recipient=record.recipient,
            customer_reference=work.customer_reference,
            filename=document_filename(record.quotation_id, record.version),
            document_sha256=document.sha256,
        )
        try:
            receipt = channel.deliver(request, data)
        except DeliveryRejected as error:
            fail(f"Rejected by the channel: {error}", _SENDING)
            return
        except DeliveryUncertain as error:
            self._store.set_status(
                tenant_id,
                delivery_id,
                DeliveryStatus.UNKNOWN,
                expected=_SENDING,
                error=clean_error(f"Outcome unknown: {error}"),
            )
            return
        except Exception as error:
            last = job.attempt >= job.max_attempts
            self._store.set_status(
                tenant_id,
                delivery_id,
                DeliveryStatus.FAILED if last else DeliveryStatus.PENDING,
                expected=_SENDING,
                error=clean_error(f"{type(error).__name__}: {error}"),
            )
            raise  # the job queue retries with backoff (or marks the job dead after the last)
        self._store.set_status(
            tenant_id,
            delivery_id,
            DeliveryStatus.AVAILABLE
            if receipt.kind is ReceiptKind.AVAILABLE
            else DeliveryStatus.SENT,
            expected=_SENDING,
            provider_reference=receipt.provider_reference,
        )

    def _document(self, tenant_id: UUID, work: DeliveryWork) -> tuple[StoredDocument, bytes]:
        """The stored approved document, rendering and storing it first if needed."""
        if work.document is not None:
            return work.document, read_verified(self._storage, work.document)
        record = work.record
        source = self._store.approved_source(tenant_id, record.quotation_id, record.version)
        if source is None:
            raise DocumentNotAvailable("This version is not approved or no longer current")
        data = self._renderer.render(source, preview=False)
        sha256 = hashlib.sha256(data).hexdigest()
        new_id = document_id(
            tenant_id, record.quotation_id, record.version, DocumentKind.APPROVED, sha256
        )
        key = document_key(tenant_id, new_id)
        self._storage.put(key, data)
        stored = self._store.save_document(
            tenant_id,
            StoredDocument(
                document_id=new_id,
                quotation_id=record.quotation_id,
                version=record.version,
                content_sha256=source.content_sha256,
                storage_key=key,
                sha256=sha256,
                size_bytes=len(data),
                renderer=self._renderer.renderer,
                created_at=self._clock(),
            ),
        )
        if stored.document_id != new_id:
            # Another attempt stored a document first (e.g. an older renderer): use that one.
            self._storage.delete(key)
            return stored, read_verified(self._storage, stored)
        return stored, data
