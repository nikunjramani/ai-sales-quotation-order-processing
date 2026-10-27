"""Outbox statuses and templates (the golden wording lives in test_quotations/test_acceptance)."""

from uuid import UUID

import pytest

from quotation_app.domain.accounts import AccountEmailPurpose
from quotation_app.domain.messages import (
    ACCOUNT_TEMPLATES,
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


@pytest.mark.parametrize("purpose", list(AccountEmailPurpose))
def test_every_account_email_has_a_subject_and_the_link(purpose: AccountEmailPurpose) -> None:
    rendered = render_template(
        ACCOUNT_TEMPLATES[purpose],
        {"link": "http://portal.example/#/x?token=t", "business": "Acme", "roles": "approver"},
    )
    assert rendered.metadata["subject"]
    assert "http://portal.example/#/x?token=t" in rendered.text


def test_account_email_values_cannot_add_lines_or_headers() -> None:
    rendered = render_template(
        TemplateKey.ACCOUNT_INVITATION,
        {"link": "L", "business": "Acme\r\nBcc: evil@example.test", "roles": "viewer"},
    )
    assert rendered.metadata["subject"] == "You are invited to Acme Bcc: evil@example.test"
    assert "\r" not in rendered.text
    assert rendered.text.startswith(
        "You are invited to join Acme Bcc: evil@example.test as viewer."
    )
    assert "within 7 days" in rendered.text
