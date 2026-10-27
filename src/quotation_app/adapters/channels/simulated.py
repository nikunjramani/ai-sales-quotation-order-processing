"""Simulated manager phone as an ApprovalNotifier (until phase 1 WI-8 moves notifications to the
outbox; then this module is deleted). Files, names and signing now live in the `simulated`
provider package, so there is one implementation of each."""

from datetime import datetime
from pathlib import Path
from uuid import UUID

from quotation_app.adapters.providers.simulated.outbox import write_message
from quotation_app.adapters.providers.simulated.provider import PROVIDER_KEY
from quotation_app.domain.messages import APPROVAL_ACTIONS, TemplateKey, render_template
from quotation_app.domain.quotations import ReviewPacket
from quotation_app.ports.channels import ChannelBinding


class SimulatedChannelNotifier:
    channel = PROVIDER_KEY

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
            "text": render_template(TemplateKey.APPROVAL_REQUEST, {"packet": packet}).text,
            "actions": list(APPROVAL_ACTIONS),
            "action_reference": action_reference,
            "expires_at": expires_at.isoformat(),
        }
        write_message(
            self._outbox, packet.tenant_id, binding.external_user_id, f"{packet.task_id}.json",
            message,
        )  # fmt: skip

    def send_notice(self, binding: ChannelBinding, notice_id: UUID, text: str) -> None:
        message = {
            "tenant_id": str(binding.tenant_id),
            "connection_id": binding.connection_id,
            "to": binding.external_user_id,
            "notice_id": str(notice_id),
            "text": text,
        }
        write_message(
            self._outbox, binding.tenant_id, binding.external_user_id, f"notice-{notice_id}.json",
            message,
        )  # fmt: skip
