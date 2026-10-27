"""API key lookup and creation.

Each key is also an `api` connection (account_ref "api-key:<id>", ADR 0018), created and
disabled together with the key, so enquiries through the API belong to a real connection.
"""

from uuid import UUID

from sqlalchemy import Engine, insert, select, text

from quotation_app.domain.connections import ConnectionStatus, Purpose
from quotation_app.domain.tenancy import Role
from quotation_app.persistence.connections import ensure_connection, set_status
from quotation_app.persistence.models import ApiKey, ConnectionRow
from quotation_app.persistence.tenancy import tenant_transaction
from quotation_app.ports.api_keys import ApiKeyRecord

# The `api` provider's key; the provider package owns it from WI-5 on.
API_PROVIDER_KEY = "api"


def api_key_account(key_id: UUID) -> str:
    """The subject an API key acts as, which is also its connection's account_ref."""
    return f"api-key:{key_id}"


class SqlApiKeyReader:
    """Runtime-role lookup. The api_key_lookup RLS policy exposes only the requested key row."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find(self, key_id: UUID) -> ApiKeyRecord | None:
        with self._engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.api_key_id', :key_id, true)"), {"key_id": str(key_id)}
            )
            row = connection.execute(
                select(
                    ApiKey.id,
                    ApiKey.tenant_id,
                    ApiKey.role,
                    ApiKey.secret_sha256,
                    ApiKey.revoked_at,
                ).where(ApiKey.id == key_id)
            ).one_or_none()
        if row is None:
            return None
        return ApiKeyRecord(
            key_id=row.id,
            tenant_id=row.tenant_id,
            role=Role(row.role),
            secret_sha256=row.secret_sha256,
            revoked=row.revoked_at is not None,
        )


def insert_api_key(
    owner_engine: Engine, key_id: UUID, tenant_id: UUID, name: str, role: Role, secret_sha256: str
) -> None:
    """Owner-only: the runtime role cannot create credentials."""
    with tenant_transaction(owner_engine, tenant_id) as connection:
        connection.execute(
            insert(ApiKey).values(
                id=key_id,
                tenant_id=tenant_id,
                name=name,
                role=role.value,
                secret_sha256=secret_sha256,
            )
        )
        ensure_connection(
            connection,
            tenant_id=tenant_id,
            provider_key=API_PROVIDER_KEY,
            account_ref=api_key_account(key_id),
            display_name=name,
            purposes=[Purpose.CUSTOMER_MESSAGES],
            created_by="api-key",
        )


def revoke_api_key(owner_engine: Engine, tenant_id: UUID, key_id: UUID) -> bool:
    with tenant_transaction(owner_engine, tenant_id) as connection:
        result = connection.execute(
            text(
                "UPDATE api_keys SET revoked_at = now() "
                "WHERE id = :id AND tenant_id = :tenant AND revoked_at IS NULL"
            ),
            {"id": key_id, "tenant": tenant_id},
        )
        if result.rowcount != 1:
            return False
        connection_id = connection.execute(
            select(ConnectionRow.id).where(
                ConnectionRow.tenant_id == tenant_id,
                ConnectionRow.provider_key == API_PROVIDER_KEY,
                ConnectionRow.account_ref == api_key_account(key_id),
            )
        ).scalar_one_or_none()
        if connection_id is not None:
            set_status(connection, tenant_id, connection_id, ConnectionStatus.DISABLED, "api-key")
        return True
