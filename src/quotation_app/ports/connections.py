"""Connection storage contracts (ADR 0018).

ConnectionStore reads one tenant's connections. HookLookup is the one cross-tenant read: the
generic webhook route knows only a connection ID from its URL, so it may reveal exactly that
row (and its webhook token hash) and nothing else, like the API key lookup.
"""

from typing import Protocol
from uuid import UUID

from quotation_app.domain.connections import Connection, Purpose


class ConnectionStore(Protocol):
    def get(self, tenant_id: UUID, connection_id: UUID) -> Connection | None: ...

    def find_by_account(
        self, tenant_id: UUID, provider_key: str, account_ref: str
    ) -> Connection | None: ...

    def list_for(self, tenant_id: UUID, purpose: Purpose | None = None) -> list[Connection]: ...

    def catalogue_sources(self, tenant_id: UUID) -> list[Connection]:
        """Active connections with Purpose.CATALOGUE (at most one, a database rule)."""
        ...


class HookLookup(Protocol):
    def find_for_hook(self, connection_id: UUID) -> tuple[Connection, str | None] | None:
        """The connection and its webhook token's SHA-256 (None: no webhook), or None."""
        ...
