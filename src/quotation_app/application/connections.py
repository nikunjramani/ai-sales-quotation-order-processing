"""Who may see a business's connections (ADR 0018, user decision P1-Q8).

Administrators (integrations:manage) see every connection, with its last error. Approvers see
only the active manager-approval connections they can link their own account to. Others see
nothing. Secrets, secret references and webhook token hashes are never part of a view.
Enabling and disabling tools comes in phase 5.
"""

from dataclasses import dataclass

from quotation_app.application.providers import ProviderRegistry
from quotation_app.domain.connections import Connection, Purpose
from quotation_app.domain.tenancy import Permission, PermissionDenied, TenantContext
from quotation_app.ports.connections import ConnectionStore


@dataclass(frozen=True)
class ConnectionView:
    connection: Connection
    provider_name: str
    show_errors: bool  # only administrators see technical errors


class ConnectionService:
    def __init__(self, connections: ConnectionStore, registry: ProviderRegistry) -> None:
        self._connections = connections
        self._registry = registry

    def list(self, context: TenantContext, purpose: Purpose | None = None) -> list[ConnectionView]:
        admin = Permission.MANAGE_INTEGRATIONS in context.permissions
        if not admin and Permission.APPROVE_QUOTATIONS not in context.permissions:
            raise PermissionDenied("Permission integrations:manage is required")
        if admin:
            rows = self._connections.list_for(context.tenant_id, purpose)
        else:
            rows = [
                row
                for row in self._connections.list_for(context.tenant_id, Purpose.MANAGER_APPROVALS)
                if row.active and (purpose is None or purpose is Purpose.MANAGER_APPROVALS)
            ]
        return [ConnectionView(row, self._provider_name(row), admin) for row in rows]

    def _provider_name(self, connection: Connection) -> str:
        provider = self._registry.find(connection.provider_key)
        return provider.display_name if provider is not None else connection.provider_key
