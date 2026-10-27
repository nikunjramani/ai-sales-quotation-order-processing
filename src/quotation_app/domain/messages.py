"""Outgoing messages: the outbox row, its statuses and the fixed wording (ADR 0018).

Everything we send (a quotation to a customer, an approval request or a notice to a manager)
is first stored as an outbound message, then handed to the connection's provider by the
send_message job. Statuses say what we actually know, never more (same rules as ADR 0015):
- pending:   stored, not yet attempted (or a transient failure that will be retried);
- sending:   being handed to the provider; a crash here means we cannot know if it arrived;
- available: pull providers (the API): the recipient can now fetch it;
- sent:      push providers: the provider accepted it;
- delivered: the provider later confirmed it reached the recipient;
- failed:    it cannot be sent (connection gone, refused, task already decided...);
- unknown:   the provider may or may not have it. Never resent automatically.

Wording is fixed in code (templates), never written by AI. A template turns parameters into the
message text plus metadata a provider may show (quotation number, task ID...). Single-use
approval tokens are never part of a stored message: they are created at send time.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from quotation_app.domain.acceptance import Offer, RecordedResponse, ResponseOutcome
from quotation_app.domain.connections import Purpose
from quotation_app.domain.quotations import ReviewPacket, quotation_number


class MessageStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    AVAILABLE = "available"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    UNKNOWN = "unknown"


# After these the worker does nothing more (a person may act on failed/unknown).
FINAL_MESSAGE_STATUSES = frozenset(
    {
        MessageStatus.AVAILABLE,
        MessageStatus.SENT,
        MessageStatus.DELIVERED,
        MessageStatus.FAILED,
        MessageStatus.UNKNOWN,
    }
)


class TemplateKey(StrEnum):
    APPROVAL_REQUEST = "approval_request"
    RESPONSE_NOTICE = "response_notice"
    QUOTATION_DOCUMENT = "quotation_document"


# The buttons an approval request offers (a provider without buttons may ignore them).
APPROVAL_ACTIONS = ("approve", "reject", "request_revision")


@dataclass(frozen=True)
class OutboundMessage:
    message_id: UUID
    tenant_id: UUID
    connection_id: UUID
    provider_key: str
    purpose: Purpose
    template_key: TemplateKey
    params: Mapping[str, str]  # IDs only; never tokens or secrets
    recipient: str
    idempotency_key: str
    body_text: str
    metadata: Mapping[str, str]
    status: MessageStatus
    document_id: UUID | None
    quotation_id: UUID | None
    version: int | None
    approval_task_id: UUID | None
    binding_id: UUID | None
    enquiry_id: UUID | None
    response_id: UUID | None
    correlation_id: UUID
    provider_message_id: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Rendered:
    text: str
    metadata: Mapping[str, str]


def render_template(key: TemplateKey, params: Mapping[str, object]) -> Rendered:
    """Fixed wording for one template. Unknown or missing parameters are a programming error."""
    if key is TemplateKey.APPROVAL_REQUEST:
        packet = params["packet"]
        assert isinstance(packet, ReviewPacket)
        return Rendered(
            _review_text(packet),
            {
                "task_id": str(packet.task_id),
                "quotation": packet.number,
                "version": str(packet.version),
            },
        )
    if key is TemplateKey.RESPONSE_NOTICE:
        offer, response = params["offer"], params["response"]
        assert isinstance(offer, Offer) and isinstance(response, RecordedResponse)
        return Rendered(_notice_text(offer, response), {"notice_id": str(response.response_id)})
    if key is TemplateKey.QUOTATION_DOCUMENT:
        # The document itself is the message. Customer-facing covering text for push providers
        # is an open decision for phase 4/5 (D22), so none is invented here.
        quotation_id, version = params["quotation_id"], params["version"]
        assert isinstance(quotation_id, UUID) and isinstance(version, int)
        return Rendered("", {"quotation": quotation_number(quotation_id), "version": str(version)})
    raise ValueError(f"Unknown template {key}")


def _review_text(packet: ReviewPacket) -> str:
    """Plain-text review summary for messaging channels. Amounts are shown exactly as stored."""
    content = packet.content
    currency = str(content["currency"])
    lines = content["lines"]
    assert isinstance(lines, list)
    text = [
        f"{packet.tenant_name}: approval needed for quotation {packet.number} "
        f"version {packet.version}",
        f"Customer reference: {packet.customer_reference or 'not given'}",
        "",
    ]
    for line in lines:
        text.append(
            f"- {line['sku']} {line['description']}: {line['quantity']} {line['unit']} x "
            f"{line['unit_price']} = {line['line_total']} {currency} "
            f"(stock: {line['stock_status']})"
        )
    text += [
        "",
        f"Subtotal {content['subtotal']} {currency}; tax {content['tax']} {currency}; "
        f"total {content['total']} {currency}",
    ]
    if content.get("stock_review_required"):
        text.append("Attention: at least one line is not confirmed as in stock.")
    text.append(f"Content hash: {packet.content_sha256[:12]}")
    return "\n".join(text)


def _notice_text(offer: Offer, response: RecordedResponse) -> str:
    total = f"{offer.content['total']} {offer.content['currency']}"
    what = {
        ResponseOutcome.ACCEPTED: "accepted",
        ResponseOutcome.DECLINED: "declined",
    }[response.outcome]
    text = (
        f"{offer.tenant_name}: the customer {what} quotation "
        f"{quotation_number(response.quotation_id)} version {response.version} (total {total})."
    )
    if response.reason:
        text += f" Reason: {response.reason}"
    return text
