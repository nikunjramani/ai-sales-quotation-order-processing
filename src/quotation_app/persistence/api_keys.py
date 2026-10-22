"""API key lookup and creation."""

from uuid import UUID

from sqlalchemy import Engine, insert, select, text

from quotation_app.domain.tenancy import Role
from quotation_app.persistence.models import ApiKey
from quotation_app.persistence.tenancy import tenant_transaction
from quotation_app.ports.api_keys import ApiKeyRecord


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


def revoke_api_key(owner_engine: Engine, tenant_id: UUID, key_id: UUID) -> bool:
    with tenant_transaction(owner_engine, tenant_id) as connection:
        result = connection.execute(
            text(
                "UPDATE api_keys SET revoked_at = now() "
                "WHERE id = :id AND tenant_id = :tenant AND revoked_at IS NULL"
            ),
            {"id": key_id, "tenant": tenant_id},
        )
        return result.rowcount == 1
