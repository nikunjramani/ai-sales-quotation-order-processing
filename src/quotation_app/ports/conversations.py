"""Contracts for writing to customers in their conversation (phase 4)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from quotation_app.domain.contacts import ConsentStatus
from quotation_app.domain.messages import TemplateKey


@dataclass(frozen=True)
class CustomerTarget:
    """Where messages about one enquiry go: its conversation's identity on its connection."""

    conversation_id: UUID
    connection_id: UUID
    identity_id: UUID
    external_id: str
    consent: ConsentStatus
    acknowledge_enquiries: bool  # the business setting (D14)
    business_name: str


class CustomerTargets(Protocol):
    def for_enquiry(self, tenant_id: UUID, enquiry_id: UUID) -> CustomerTarget | None:
        """None when the enquiry has no conversation (an API enquiry without a reference)."""
        ...

    def consent(self, tenant_id: UUID, connection_id: UUID, external_id: str) -> ConsentStatus:
        """The identity's consent now (implied for an unknown identity)."""
        ...

    def for_identity(
        self, tenant_id: UUID, connection_id: UUID, external_id: str
    ) -> CustomerTarget | None:
        """The conversation of one identity (for consent confirmations)."""
        ...

    def set_consent(
        self,
        tenant_id: UUID,
        connection_id: UUID,
        external_id: str,
        status: ConsentStatus,
        source: str,
    ) -> bool:
        """Change the identity's consent; False if unknown or already in that state."""
        ...


class CustomerNotifier(Protocol):
    """What the workflows need to write to a customer (implemented by CustomerMessenger)."""

    def send(
        self,
        tenant_id: UUID,
        enquiry_id: UUID,
        template: TemplateKey,
        render: Mapping[str, object],
        idempotency_key: str,
        correlation_id: UUID,
    ) -> UUID | None: ...
