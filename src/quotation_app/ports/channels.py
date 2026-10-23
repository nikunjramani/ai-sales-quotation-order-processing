"""Manager approval channel contracts: bindings, action references and review delivery.

A channel binding links an internal manager (subject) to one external account on one provider
connection. It is created only through enrollment (proof of control) and can be revoked.
Action references are opaque, expiring, single-use tokens bound to one task and one binding.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from quotation_app.domain.quotations import ReviewPacket


@dataclass(frozen=True)
class ChannelBinding:
    binding_id: UUID
    tenant_id: UUID
    subject: str
    channel: str
    connection_id: str
    external_user_id: str
    created_at: datetime
    revoked_at: datetime | None

    @property
    def active(self) -> bool:
        return self.revoked_at is None


@dataclass(frozen=True)
class ActionReference:
    reference_id: UUID
    task_id: UUID
    binding_id: UUID
    content_sha256: str  # of the task's version
    expires_at: datetime
    consumed_at: datetime | None


class ApprovalNotifier(Protocol):
    """Delivers messages to one bound manager account. Raises on failure (retried)."""

    channel: str

    def send_review(
        self,
        binding: ChannelBinding,
        packet: ReviewPacket,
        action_reference: str,
        expires_at: datetime,
    ) -> None: ...

    def send_notice(self, binding: ChannelBinding, notice_id: UUID, text: str) -> None:
        """An information-only message (e.g. "customer accepted Q-..."); it has no actions.

        notice_id identifies the event, so a provider can drop a repeated delivery.
        """
        ...


class NotificationStore(Protocol):
    def review_packet(self, tenant_id: UUID, task_id: UUID) -> ReviewPacket | None:
        """The packet for a task that is still pending; None otherwise."""
        ...

    def approver_bindings(self, tenant_id: UUID) -> list[ChannelBinding]:
        """Active bindings whose subject currently holds the approver role."""
        ...

    def prepare_reference(
        self,
        tenant_id: UUID,
        task_id: UUID,
        binding_id: UUID,
        token_sha256: str,
        expires_at: datetime,
    ) -> UUID | None:
        """Create (or rotate, if never sent) the reference; None if it was already sent."""
        ...

    def mark_sent(self, tenant_id: UUID, reference_id: UUID) -> None: ...


class ChannelStore(Protocol):
    def create_enrollment(
        self, tenant_id: UUID, subject: str, channel: str, code_sha256: str, expires_at: datetime
    ) -> None: ...

    def enroll(
        self,
        tenant_id: UUID,
        channel: str,
        connection_id: str,
        external_user_id: str,
        code_sha256: str,
        now: datetime,
    ) -> ChannelBinding | None:
        """Consume a valid enrollment code and create the binding atomically.

        A replay by the same external user returns the binding created the first time; an
        unknown, expired or already used code returns None.
        """
        ...

    def find_reference(
        self, tenant_id: UUID, token_sha256: str
    ) -> tuple[ActionReference, ChannelBinding] | None: ...

    def bindings_for(self, tenant_id: UUID, subject: str | None) -> list[ChannelBinding]:
        """A subject's bindings, or all of the tenant's bindings when subject is None."""
        ...

    def revoke(self, tenant_id: UUID, binding_id: UUID, subject: str | None) -> bool:
        """Revoke an active binding (only the subject's own unless subject is None)."""
        ...
