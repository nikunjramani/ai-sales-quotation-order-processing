"""The Provider contract: what every tool package (api, simulated, later Telegram...) offers.

A provider package registers a factory under the Python entry point group
`quotation_app.providers`; the registry builds every installed provider at start-up. Adding a
tool is one package plus one entry point. No core code changes (ADR 0018,
.docs/development/adding-providers.md).

Rules for implementations:
- Never take the tenant from a request. The tenant is always the connection's.
- verify_inbound runs on the raw bytes before parse_inbound; a forged or stale request raises
  InboundRejected.
- send raises SendRejected when the provider refused for good and SendUncertain when the
  message may have been accepted (it is then never resent). Any other exception means nothing
  was handed over, so the attempt may be retried.
- Operations a provider does not support raise OperationUnsupported, never a fake success.

Phase 1 needs the operations below; later phases add theirs (resume, handshake, platform
webhooks, order_writer) as listed in the shared contracts.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID

from quotation_app.domain.connections import Capabilities, Connection, Purpose
from quotation_app.domain.intake import InboundEvent
from quotation_app.ports.catalogue_admin import CatalogueReadStore
from quotation_app.ports.erp import ErpReader
from quotation_app.ports.secrets import SecretStore


@dataclass(frozen=True)
class InboundRequest:
    headers: Mapping[str, str]  # names in lower case
    body: bytes
    query: Mapping[str, str]
    received_at: datetime


@dataclass(frozen=True)
class Attachment:
    filename: str
    content_type: str
    data: bytes
    sha256: str


@dataclass(frozen=True)
class RenderedMessage:
    """One outbox message ready for a provider. message_id doubles as the idempotency key."""

    message_id: UUID
    idempotency_key: str
    recipient: str
    text: str
    metadata: Mapping[str, str]  # e.g. task_id, quotation, version, notice_id
    actions: tuple[str, ...] = ()
    action_reference: str | None = None  # created at send time, never stored in the outbox
    expires_at: datetime | None = None
    attachment: Attachment | None = None


class ReceiptKind(StrEnum):
    SENT = "sent"  # push: the provider accepted it
    AVAILABLE = "available"  # pull: the recipient can now fetch it


@dataclass(frozen=True)
class SendReceipt:
    kind: ReceiptKind
    provider_message_id: str | None = None


@dataclass(frozen=True)
class TestResult:
    """Outcome of a provider's connection test (not a pytest test class)."""

    __test__ = False
    ok: bool
    detail: str | None = None


class InboundRejected(Exception):
    """The callback is not genuinely from the provider (bad signature, stale timestamp)."""


class InvalidInbound(Exception):
    """The callback is genuine but its content cannot be understood."""


class SendRejected(Exception):
    """The provider refused the message for good (bad address, blocked, too large...)."""


class SendUncertain(Exception):
    """The message may have reached the provider (e.g. a timeout after sending)."""


class OperationUnsupported(Exception):
    """This provider does not offer the requested operation."""


@dataclass(frozen=True)
class ProviderEnvironment:
    """Generic dependencies given to every provider factory; never provider-named settings."""

    environment: str  # development | test | production
    storage_dir: Path
    options: Mapping[str, object] = field(default_factory=dict)
    # Our own catalogue tables, bound to the running process's database role (phase 3).
    catalogue_store: CatalogueReadStore | None = None


class Provider(Protocol):
    key: str
    display_name: str
    purposes: frozenset[Purpose]
    capabilities: Capabilities
    dev_only: bool  # the registry skips it in production

    def test(self, conn: Connection, secrets: SecretStore) -> TestResult: ...

    def verify_inbound(
        self, conn: Connection, secrets: SecretStore, request: InboundRequest
    ) -> None: ...

    def parse_inbound(self, conn: Connection, request: InboundRequest) -> Sequence[InboundEvent]:
        """Normalised events; raises InvalidInbound. Each carries a stable provider_event_id."""
        ...

    def send(
        self, conn: Connection, secrets: SecretStore, message: RenderedMessage
    ) -> SendReceipt: ...

    def catalogue_reader(self, conn: Connection, secrets: SecretStore) -> ErpReader:
        """The product source behind a connection with Purpose.CATALOGUE."""
        ...


type ProviderFactory = Callable[[ProviderEnvironment], Provider]
