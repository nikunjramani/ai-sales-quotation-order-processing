"""Customer answers, staff withdrawal and expiry of issued quotations (M6, ADR 0016).

- respond: the customer's system accepts or declines the exact version it holds (API key).
  Accepting re-prices the lines from the ERP; any price difference refuses it and stores a
  revised version that goes through manager approval (the workflow resumes). ERP errors
  propagate, so nothing is recorded and the caller can retry.
- withdraw: a sales operator or approver closes an issued, unanswered quotation with a reason.
- expire: the job queued for "valid until" closes a quotation nobody answered.
- ResponseNotificationHandler tells managers' linked channels about accepted/declined answers.

Every answer is recorded once (idempotency key, append-only); a replay returns the first result.
"""

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from quotation_app.application.pricing import QuotationPricingService
from quotation_app.domain.acceptance import (
    SYSTEM_SUBJECT,
    CustomerStatus,
    NotCurrentOffer,
    Offer,
    OfferNotOpen,
    PricesChanged,
    RecordedResponse,
    ResponseAction,
    ResponseConflict,
    ResponseOutcome,
    ResponseRequest,
    price_differences,
)
from quotation_app.domain.documents import DocumentNotAvailable
from quotation_app.domain.intake import validate_idempotency_key
from quotation_app.domain.jobs import PermanentJobError
from quotation_app.domain.messages import TemplateKey, render_template
from quotation_app.domain.pricing import PricingRejected, RequestedLine
from quotation_app.domain.quotations import (
    QuotationNotFound,
    QuotationStatus,
    clean_reason,
    content_sha256,
    pricing_issues_content,
    quotation_content,
)
from quotation_app.domain.tenancy import Permission, PermissionDenied, Role, TenantContext
from quotation_app.ports.acceptance import NewResponse, ResponseStore, RevisedContent
from quotation_app.ports.channels import ApprovalNotifier, NotificationStore
from quotation_app.ports.jobs import ClaimedJob

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


# User decision (ADR 0016): sales operators and approvers withdraw; administrators do not.
WITHDRAWING_ROLES = frozenset({Role.SALES_OPERATOR, Role.APPROVER})


class NotIssued(Exception):
    """The quotation has not been delivered to the customer, so there is nothing to withdraw."""


class NotDueYet(Exception):
    """An expiry job ran before valid_until (e.g. clock differences). Retried later."""


class QuotationResponseService:
    def __init__(
        self,
        store: ResponseStore,
        pricing: QuotationPricingService,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._pricing = pricing
        self._clock = clock

    # --- customer ---------------------------------------------------------------------
    def offer(self, context: TenantContext, enquiry_id: UUID, channel: str) -> Offer:
        """The offer the customer holds for its enquiry (any status)."""
        context.require(Permission.VIEW_ENQUIRIES)
        offer = self._store.offer_for_enquiry(context.tenant_id, enquiry_id, channel)
        if offer is None:
            raise DocumentNotAvailable("No quotation has been issued for this enquiry yet")
        return offer

    def respond(
        self,
        context: TenantContext,
        enquiry_id: UUID,
        channel: str,
        idempotency_key: str,
        request: ResponseRequest,
    ) -> tuple[RecordedResponse, bool]:
        """Record an accept/decline; returns (response, replayed).

        Raises DocumentNotAvailable (nothing issued), NotCurrentOffer (wrong version or hash),
        OfferNotOpen (answered, expired, withdrawn, being revised), ResponseConflict (key reused
        for a different answer), PricesChanged (acceptance refused; recorded and revised) and
        ErpError (nothing recorded; retry).
        """
        context.require(Permission.RESPOND_QUOTATIONS)
        key = validate_idempotency_key(idempotency_key)
        fingerprint = request.fingerprint()
        earlier = self._replay(context.tenant_id, key, fingerprint)
        if earlier is not None:
            return earlier, True
        offer = self.offer(context, enquiry_id, channel)
        if request.version != offer.version or request.content_sha256 != offer.content_sha256:
            raise NotCurrentOffer("This is not the quotation version currently offered")
        now = self._clock()
        self._require_open(offer, now)
        if request.action is ResponseAction.DECLINE:
            response = NewResponse(
                ResponseOutcome.DECLINED, context.subject, request.reason, key, fingerprint
            )
        else:
            response = self._acceptance(offer, context.subject, key, fingerprint)
        recorded = self._store.record(context.tenant_id, offer, response, now)
        self._raise_if_refused(recorded)
        return recorded, False

    def status_of(self, offer: Offer) -> CustomerStatus:
        return offer.customer_status(self._clock())

    # --- staff ------------------------------------------------------------------------
    def history(
        self, context: TenantContext, quotation_id: UUID
    ) -> tuple[Offer | None, list[RecordedResponse]]:
        """The issued offer (if any) and every answer, for the portal."""
        context.require(Permission.VIEW_QUOTATIONS)
        return (
            self._store.offer_for_quotation(context.tenant_id, quotation_id),
            self._store.responses(context.tenant_id, quotation_id),
        )

    def withdraw(
        self, context: TenantContext, quotation_id: UUID, command_id: UUID, reason: str | None
    ) -> tuple[RecordedResponse, bool]:
        if not context.roles & WITHDRAWING_ROLES:
            raise PermissionDenied("Only sales operators and approvers can withdraw quotations")
        reason = clean_reason(reason)
        if reason is None:
            raise ValueError("A reason is required to withdraw a quotation")
        key = f"withdraw:{command_id}"
        fingerprint = ResponseRequest(ResponseAction.DECLINE, 0, "0" * 64, reason).fingerprint()
        earlier = self._replay(context.tenant_id, key, fingerprint)
        if earlier is not None:
            if earlier.quotation_id != quotation_id:
                raise ResponseConflict("This command ID was used for another quotation")
            return earlier, True
        offer = self._store.offer_for_quotation(context.tenant_id, quotation_id)
        if offer is None:
            raise NotIssued(
                "Only a quotation that has been issued to the customer can be withdrawn"
            )
        now = self._clock()
        self._require_open(offer, now)
        response = NewResponse(ResponseOutcome.WITHDRAWN, context.subject, reason, key, fingerprint)
        return self._store.record(context.tenant_id, offer, response, now), False

    # --- expiry job -------------------------------------------------------------------
    def expire(self, tenant_id: UUID, quotation_id: UUID, version: int) -> RecordedResponse | None:
        """Close the version if it is still unanswered at valid_until; otherwise do nothing."""
        offer = self._store.offer_for_quotation(tenant_id, quotation_id)
        if (
            offer is None
            or offer.version != version
            or offer.status is not QuotationStatus.APPROVED
            or offer.current_version != version
        ):
            return None  # answered, withdrawn, revised or already expired
        now = self._clock()
        if now < offer.valid_until:
            raise NotDueYet("The quotation is still valid")
        return self._record_expiry(offer, now)

    # --- helpers ----------------------------------------------------------------------
    def _replay(self, tenant_id: UUID, key: str, fingerprint: str) -> RecordedResponse | None:
        found = self._store.find_response(tenant_id, key)
        if found is None:
            return None
        recorded, stored_fingerprint = found
        if stored_fingerprint != fingerprint:
            raise ResponseConflict("This Idempotency-Key was already used for a different answer")
        self._raise_if_refused(recorded)
        return recorded

    def _require_open(self, offer: Offer, now: datetime) -> None:
        status = offer.customer_status(now)
        if status is CustomerStatus.OPEN:
            return
        if status is CustomerStatus.EXPIRED and offer.status is QuotationStatus.APPROVED:
            self._record_expiry(offer, now)  # validity ended before the expiry job ran
        raise OfferNotOpen(status)

    def _record_expiry(self, offer: Offer, now: datetime) -> RecordedResponse | None:
        key = f"expire:{offer.quotation_id}:{offer.version}"
        response = NewResponse(ResponseOutcome.EXPIRED, SYSTEM_SUBJECT, None, key, key)
        try:
            return self._store.record(offer.tenant_id, offer, response, now)
        except OfferNotOpen:
            return None  # answered or closed meanwhile

    def _acceptance(self, offer: Offer, actor: str, key: str, fingerprint: str) -> NewResponse:
        lines = offer.content["lines"]
        assert isinstance(lines, list)
        requested = [
            RequestedLine(str(line["sku"]), Decimal(str(line["quantity"])), str(line["unit"]))
            for line in lines
        ]
        # Re-pricing runs as the workflow's system identity: the customer never drafts.
        system = TenantContext(offer.tenant_id, SYSTEM_SUBJECT, frozenset({Role.SALES_OPERATOR}))
        outcome = self._pricing.price(system, requested)  # ErpError propagates: retry later
        if isinstance(outcome, PricingRejected):
            issues = pricing_issues_content(outcome.issues)
            return NewResponse(
                ResponseOutcome.REFUSED_CHANGED,
                actor,
                None,
                key,
                fingerprint,
                tuple(f"{issue.sku}: {issue.message}" for issue in outcome.issues),
                RevisedContent(None, None, issues),
            )
        current = quotation_content(outcome)
        differences = price_differences(offer.content, current)
        if not differences:
            return NewResponse(ResponseOutcome.ACCEPTED, actor, None, key, fingerprint)
        return NewResponse(
            ResponseOutcome.REFUSED_CHANGED,
            actor,
            None,
            key,
            fingerprint,
            differences,
            RevisedContent(current, content_sha256(current), None),
        )

    @staticmethod
    def _raise_if_refused(recorded: RecordedResponse) -> None:
        if recorded.outcome is ResponseOutcome.REFUSED_CHANGED:
            raise PricesChanged(recorded.differences, recorded.revised_version)


class QuotationExpiryHandler:
    """Job handler for expire_quotation (queued for the moment validity ends)."""

    def __init__(self, service: QuotationResponseService) -> None:
        self._service = service

    def __call__(self, job: ClaimedJob) -> None:
        try:
            quotation_id = UUID(job.payload["quotation_id"])
            version = int(job.payload["version"])
        except (KeyError, ValueError):
            raise PermanentJobError("Job payload has no valid quotation_id/version") from None
        self._service.expire(job.tenant_id, quotation_id, version)


class ResponseNotificationHandler:
    """Job handler for notify_response: tell managers' linked channels about an answer.

    At least once: if one account fails, the retry may repeat the notice to the others; each
    notice carries the response ID so a provider (or the simulated outbox) can drop repeats.
    """

    def __init__(
        self,
        responses: ResponseStore,
        bindings: NotificationStore,
        notifiers: Mapping[str, ApprovalNotifier],
    ) -> None:
        self._responses = responses
        self._bindings = bindings
        self._notifiers = dict(notifiers)

    def __call__(self, job: ClaimedJob) -> None:
        try:
            response_id = UUID(job.payload["response_id"])
        except (KeyError, ValueError):
            raise PermanentJobError("Job payload has no valid response_id") from None
        response = self._responses.response(job.tenant_id, response_id)
        if response is None:
            raise PermanentJobError("Response not found")
        offer = self._responses.offer_for_quotation(job.tenant_id, response.quotation_id)
        if offer is None:
            raise QuotationNotFound("Quotation not found")
        text = render_template(
            TemplateKey.RESPONSE_NOTICE, {"offer": offer, "response": response}
        ).text
        for binding in self._bindings.approver_bindings(job.tenant_id):
            notifier = self._notifiers.get(binding.channel)
            if notifier is None:
                logger.warning("No notifier configured for channel %s", binding.channel)
                continue
            notifier.send_notice(binding, response.response_id, text)
