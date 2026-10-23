"""Version snapshots, content hashing, decision commands and review text."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from quotation_app.adapters.erp.simulated import SimulatedErp
from quotation_app.application.pricing import QuotationPricingService
from quotation_app.domain.pricing import PricedQuotation, RequestedLine
from quotation_app.domain.quotations import (
    ApprovalAction,
    DecisionCommand,
    ReviewPacket,
    content_sha256,
    quotation_content,
    quotation_number,
    render_review_text,
)
from quotation_app.domain.tenancy import Role, TenantContext


@pytest.fixture
def priced(
    simulated_erp: SimulatedErp,
    policy_reader: Any,
    now: datetime,
    make_context: Callable[[UUID, Role], TenantContext],
    industrial_tenant: UUID,
) -> PricedQuotation:
    service = QuotationPricingService(simulated_erp, policy_reader, clock=lambda: now)
    outcome = service.price(
        make_context(industrial_tenant, Role.SALES_OPERATOR),
        [
            RequestedLine("IND-FAN-450", Decimal(2), "each"),
            RequestedLine("IND-CABLE-2C", Decimal("12.5"), "metre"),
        ],
    )
    assert isinstance(outcome, PricedQuotation)
    return outcome


def command(**changes: Any) -> DecisionCommand:
    values: dict[str, Any] = {
        "command_id": uuid4(),
        "tenant_id": uuid4(),
        "task_id": uuid4(),
        "content_sha256": "a" * 64,
        "action": ApprovalAction.APPROVE,
        "reason": None,
        "transport": "portal",
        "evidence_ref": None,
        "received_at": datetime(2026, 10, 22, tzinfo=UTC),
    }
    values.update(changes)
    return DecisionCommand(**values)


def test_content_keeps_exact_amounts_and_evidence(priced: PricedQuotation) -> None:
    content = quotation_content(priced)
    assert content["currency"] == "INR"
    assert (content["subtotal"], content["tax"], content["total"]) == (
        "8980.00",
        "1616.40",
        "10596.40",
    )
    lines = content["lines"]
    assert isinstance(lines, list)
    assert lines[0]["unit_price"] == "4250.00" and lines[0]["price_list_id"] == "STD-2026"
    assert lines[1]["stock_status"] == "unknown" and lines[1]["stock_available"] is None
    assert content["stock_review_required"] is True


def test_hash_is_stable_and_changes_with_any_value(priced: PricedQuotation) -> None:
    content = quotation_content(priced)
    reordered = dict(reversed(list(content.items())))
    assert content_sha256(content) == content_sha256(reordered)
    changed = {**content, "total": "10596.41"}
    assert content_sha256(changed) != content_sha256(content)


def test_reject_and_revision_need_a_reason() -> None:
    assert command().reason is None
    with pytest.raises(ValueError, match="reason"):
        command(action=ApprovalAction.REJECT, reason="   ")
    assert command(action=ApprovalAction.REQUEST_REVISION, reason=" fix qty ").reason == "fix qty"
    with pytest.raises(ValueError, match="1000"):
        command(action=ApprovalAction.REJECT, reason="x" * 1001)


@pytest.mark.parametrize(
    "changes",
    [
        {"content_sha256": "A" * 64},
        {"content_sha256": "short"},
        {"received_at": datetime(2026, 10, 22)},
        {"transport": ""},
    ],
)
def test_invalid_commands_are_refused(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        command(**changes)


def test_review_text_shows_what_is_being_approved(priced: PricedQuotation) -> None:
    content = quotation_content(priced)
    quotation_id = UUID("1a2b3c4d-0000-4000-8000-000000000000")
    packet = ReviewPacket(
        uuid4(), "Demo Industrial", uuid4(), quotation_id, 2, content_sha256(content), None,
        content,
    )  # fmt: skip
    text = render_review_text(packet)
    assert quotation_number(quotation_id) == "Q-1A2B3C4D"
    assert "quotation Q-1A2B3C4D version 2" in text
    assert "IND-FAN-450 Industrial exhaust fan 450 mm: 2 each x 4250.00 = 8500.00 INR" in text
    assert "total 10596.40 INR" in text
    assert "not confirmed as in stock" in text
    assert "Customer reference: not given" in text
