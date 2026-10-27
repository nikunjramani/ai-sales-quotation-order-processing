"""The simulated provider: byte-compatible outbox files, signatures, parsing and catalogue."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from quotation_app.adapters.providers.simulated import SimulatedProvider
from quotation_app.adapters.providers.simulated.signing import SIGNATURE_HEADER, sign
from quotation_app.domain.connections import Connection, ConnectionStatus, Purpose
from quotation_app.domain.intake import ManagerAction
from quotation_app.domain.tenancy import Role, TenantContext
from quotation_app.ports.providers import (
    InboundRejected,
    InboundRequest,
    InvalidInbound,
    OperationUnsupported,
    ReceiptKind,
    RenderedMessage,
    SendRejected,
)
from quotation_app.ports.secrets import SecretNotFound

TENANT = UUID("00000000-0000-4000-8000-000000000001")
TASK = "00000000-0000-4000-8000-0000000000aa"
NOTICE = "00000000-0000-4000-8000-0000000000bb"
NOW = datetime(2026, 10, 27, tzinfo=UTC)


class OneSecret:
    def get(self, tenant_id: UUID, reference: str) -> str:
        if (tenant_id, reference) != (TENANT, "local:demo"):
            raise SecretNotFound("Secret not found")
        return "dev-secret"

    def put(self, tenant_id: UUID, name: str, value: str) -> str:
        raise NotImplementedError

    def delete(self, tenant_id: UUID, reference: str) -> None:
        raise NotImplementedError


def connection(**changes: Any) -> Connection:
    values: dict[str, Any] = {
        "connection_id": uuid4(), "tenant_id": TENANT, "provider_key": "simulated",
        "display_name": "Phone",
        "purposes": frozenset({Purpose.MANAGER_APPROVALS, Purpose.CATALOGUE}),
        "config": {"catalogue": "industrial"}, "secret_refs": {"signing_secret": "local:demo"},
        "account_ref": "simulated-local", "status": ConnectionStatus.ACTIVE, "last_error": None,
        "created_by": "seed", "created_at": NOW, "updated_at": NOW,
    }  # fmt: skip
    values.update(changes)
    return Connection(**values)


def message(**metadata: str) -> RenderedMessage:
    return RenderedMessage(
        uuid4(), "key", "manager/phone", "Demo: approval needed", metadata,
        actions=("approve", "reject", "request_revision"), action_reference="ref-123",
        expires_at=datetime(2026, 10, 28, tzinfo=UTC),
    )  # fmt: skip


def test_review_and_notice_files_match_the_old_notifier(tmp_path: Path) -> None:
    provider = SimulatedProvider(tmp_path)
    review = message(task_id=TASK, quotation="Q-1A2B3C4D", version="3")
    receipt = provider.send(connection(), OneSecret(), review)
    assert receipt.kind is ReceiptKind.SENT
    path = tmp_path / str(TENANT) / "manager_phone" / f"{TASK}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert list(data) == [
        "tenant_id", "connection_id", "to", "task_id", "quotation", "version", "text",
        "actions", "action_reference", "expires_at",
    ]  # fmt: skip
    assert (data["connection_id"], data["version"], data["expires_at"]) == (
        "simulated-local", 3, "2026-10-28T00:00:00+00:00",
    )  # fmt: skip
    provider.send(connection(), OneSecret(), message(notice_id=NOTICE))
    notice = json.loads((path.parent / f"notice-{NOTICE}.json").read_text(encoding="utf-8"))
    assert list(notice) == ["tenant_id", "connection_id", "to", "notice_id", "text"]
    with pytest.raises(SendRejected):
        provider.send(connection(), OneSecret(), message(quotation="Q-1"))


def test_signatures_use_the_connections_own_secret() -> None:
    provider = SimulatedProvider(Path("unused"))
    body = b'{"event_id": "e"}'
    good = InboundRequest({SIGNATURE_HEADER.lower(): sign("dev-secret", body)}, body, {}, NOW)
    provider.verify_inbound(connection(), OneSecret(), good)
    for bad in (
        InboundRequest({SIGNATURE_HEADER.lower(): sign("other", body)}, body, {}, NOW),
        InboundRequest({}, body, {}, NOW),
    ):
        with pytest.raises(InboundRejected):
            provider.verify_inbound(connection(), OneSecret(), bad)
    with pytest.raises(InboundRejected):  # no signing secret configured
        provider.verify_inbound(connection(secret_refs={}), OneSecret(), good)
    with pytest.raises(InboundRejected):  # another business's reference does not resolve
        provider.verify_inbound(connection(tenant_id=uuid4()), OneSecret(), good)


def test_parsing_gives_manager_actions_and_refuses_tenant_fields() -> None:
    provider = SimulatedProvider(Path("unused"))
    body = json.dumps(
        {"event_id": "evt-9", "external_user_id": "phone", "type": "decision",
         "action_reference": "ref", "action": "approve"}
    ).encode()  # fmt: skip
    [event] = provider.parse_inbound(connection(), InboundRequest({}, body, {}, NOW))
    assert event == ManagerAction("evt-9", "phone", "decision", None, "ref", "approve", None)
    for bad in (b"[]", b'{"event_id": "e", "tenant_id": "x"}'):
        with pytest.raises(InvalidInbound):
            provider.parse_inbound(connection(), InboundRequest({}, bad, {}, NOW))


def test_catalogue_reader_is_the_named_demo_catalogue_for_that_business() -> None:
    provider = SimulatedProvider(Path("unused"))
    reader = provider.catalogue_reader(connection(), OneSecret())
    context = TenantContext(TENANT, "system", frozenset({Role.SALES_OPERATOR}))
    assert "IND-FAN-450" in reader.get_products(context, ["IND-FAN-450"])
    assert provider.catalogue_reader(connection(), OneSecret()) is reader  # same state
    with pytest.raises(OperationUnsupported):
        provider.catalogue_reader(connection(config={"catalogue": "unknown"}), OneSecret())
    with pytest.raises(OperationUnsupported):
        no_catalogue = connection(purposes=frozenset({Purpose.MANAGER_APPROVALS}))
        provider.catalogue_reader(no_catalogue, OneSecret())
