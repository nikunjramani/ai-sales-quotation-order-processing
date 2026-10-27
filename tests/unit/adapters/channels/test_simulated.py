"""Golden outbox files of the simulated manager phone.

The demo page and scripts/simulated_channel.py read these files, so their names and JSON keys
must stay byte-compatible when phase 1 moves the adapter onto the provider framework.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from quotation_app.adapters.channels.simulated import SimulatedChannelNotifier
from quotation_app.domain.quotations import ReviewPacket
from quotation_app.ports.channels import ChannelBinding

TENANT = UUID("00000000-0000-4000-8000-000000000001")
TASK = UUID("00000000-0000-4000-8000-0000000000aa")
QUOTATION = UUID("1a2b3c4d-0000-4000-8000-000000000000")
NOTICE = UUID("00000000-0000-4000-8000-0000000000bb")
CONTENT: dict[str, object] = {
    "currency": "INR",
    "lines": [],
    "subtotal": "0.00",
    "tax": "0.00",
    "total": "0.00",
}


def binding() -> ChannelBinding:
    return ChannelBinding(
        UUID("00000000-0000-4000-8000-0000000000cc"),
        TENANT,
        "manager@industrial.example",
        "simulated",
        "simulated-local",
        "manager/phone",
        datetime(2026, 10, 27, tzinfo=UTC),
        None,
    )


def test_review_file_name_and_keys(tmp_path: Path) -> None:
    packet = ReviewPacket(TENANT, "Demo", TASK, QUOTATION, 3, "f" * 64, "PO-1", CONTENT)
    expires = datetime(2026, 10, 28, tzinfo=UTC)
    SimulatedChannelNotifier(tmp_path).send_review(binding(), packet, "ref-123", expires)

    path = tmp_path / str(TENANT) / "manager_phone" / f"{TASK}.json"
    message = json.loads(path.read_text(encoding="utf-8"))
    assert list(message) == [
        "tenant_id",
        "connection_id",
        "to",
        "task_id",
        "quotation",
        "version",
        "text",
        "actions",
        "action_reference",
        "expires_at",
    ]
    assert message["tenant_id"] == str(TENANT)
    assert message["connection_id"] == "simulated-local"
    assert message["to"] == "manager/phone"
    assert message["task_id"] == str(TASK)
    assert (message["quotation"], message["version"]) == ("Q-1A2B3C4D", 3)
    assert message["text"].startswith("Demo: approval needed for quotation Q-1A2B3C4D version 3")
    assert message["actions"] == ["approve", "reject", "request_revision"]
    assert message["action_reference"] == "ref-123"
    assert message["expires_at"] == "2026-10-28T00:00:00+00:00"
    assert [p.name for p in path.parent.iterdir()] == [f"{TASK}.json"]  # no temp files left


def test_notice_file_name_and_keys(tmp_path: Path) -> None:
    notifier = SimulatedChannelNotifier(tmp_path)
    notifier.send_notice(binding(), NOTICE, "The customer accepted")
    notifier.send_notice(binding(), NOTICE, "The customer accepted")  # a repeat replaces

    folder = tmp_path / str(TENANT) / "manager_phone"
    assert [p.name for p in folder.iterdir()] == [f"notice-{NOTICE}.json"]
    message = json.loads((folder / f"notice-{NOTICE}.json").read_text(encoding="utf-8"))
    assert message == {
        "tenant_id": str(TENANT),
        "connection_id": "simulated-local",
        "to": "manager/phone",
        "notice_id": str(NOTICE),
        "text": "The customer accepted",
    }
