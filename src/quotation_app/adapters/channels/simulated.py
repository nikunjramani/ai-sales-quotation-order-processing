"""Simulated messaging provider for manager approvals (development and tests).

It behaves like a real provider in the ways that matter for security:
- Outbound: review messages are "delivered" as JSON files in a local outbox folder (a fake
  phone), one per bound account and task, including the action reference a button would carry.
- Inbound: events are signed with HMAC-SHA256 using a shared secret, the way webhook
  providers sign callbacks. Unsigned or altered events are rejected before any processing.

The outbox lives under the git-ignored storage folder. It contains live action references, so
treat it like a mailbox: development only.
"""

import hashlib
import hmac
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from quotation_app.domain.quotations import ApprovalChannel, ReviewPacket, render_review_text
from quotation_app.ports.channels import ChannelBinding

SIGNATURE_HEADER = "X-Simulated-Signature"
DEFAULT_CONNECTION_ID = "simulated-local"
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.@-]")


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def signature_valid(secret: str, body: bytes, signature: str | None) -> bool:
    return signature is not None and hmac.compare_digest(sign(secret, body), signature)


class SimulatedChannelNotifier:
    channel = ApprovalChannel.SIMULATED.value

    def __init__(self, outbox_dir: Path) -> None:
        self._outbox = outbox_dir.resolve()

    def send_review(
        self,
        binding: ChannelBinding,
        packet: ReviewPacket,
        action_reference: str,
        expires_at: datetime,
    ) -> None:
        message = {
            "tenant_id": str(packet.tenant_id),
            "connection_id": binding.connection_id,
            "to": binding.external_user_id,
            "task_id": str(packet.task_id),
            "quotation": packet.number,
            "version": packet.version,
            "text": render_review_text(packet),
            "actions": ["approve", "reject", "request_revision"],
            "action_reference": action_reference,
            "expires_at": expires_at.isoformat(),
        }
        folder = (
            self._outbox / str(packet.tenant_id) / _SAFE_NAME.sub("_", binding.external_user_id)
        )
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{packet.task_id}.json"
        descriptor, temporary = tempfile.mkstemp(dir=folder, prefix=".message-")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(message, stream, indent=2)
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
