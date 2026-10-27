"""Outbox statuses and templates (the golden wording lives in test_quotations/test_acceptance)."""

from uuid import UUID

import pytest

from quotation_app.domain.messages import (
    FINAL_MESSAGE_STATUSES,
    MessageStatus,
    TemplateKey,
    render_template,
)


def test_only_pending_and_sending_are_unfinished() -> None:
    assert set(MessageStatus) - FINAL_MESSAGE_STATUSES == {
        MessageStatus.PENDING,
        MessageStatus.SENDING,
    }


def test_quotation_document_has_no_invented_covering_text() -> None:
    quotation_id = UUID("1a2b3c4d-0000-4000-8000-000000000000")
    rendered = render_template(
        TemplateKey.QUOTATION_DOCUMENT, {"quotation_id": quotation_id, "version": 3}
    )
    assert rendered.text == ""
    assert rendered.metadata == {"quotation": "Q-1A2B3C4D", "version": "3"}


def test_missing_parameters_are_a_programming_error() -> None:
    with pytest.raises(KeyError):
        render_template(TemplateKey.APPROVAL_REQUEST, {})
