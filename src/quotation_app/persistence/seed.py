"""Idempotently insert two fictional tenants for local development, using owner access."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from quotation_app.config import Settings
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.models import Tenant

DEMO_TENANTS = (
    (UUID("11111111-1111-4111-8111-111111111111"), "Demo Industrial Supplies"),
    (UUID("22222222-2222-4222-8222-222222222222"), "Demo Office Equipment"),
)


def seed_demo_tenants(settings: Settings) -> None:
    if settings.environment not in {"development", "test"}:
        raise ValueError("Demo data seeding is disabled outside development/test")
    engine = build_engine(settings.migration_url())
    try:
        with engine.begin() as connection:
            for tenant_id, name in DEMO_TENANTS:
                # FORCE RLS also applies to the owner. Context is transaction-local.
                connection.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                connection.execute(
                    insert(Tenant)
                    .values(id=tenant_id, name=name)
                    .on_conflict_do_nothing(index_elements=["id"])
                )
    finally:
        engine.dispose()


def main() -> None:
    seed_demo_tenants(Settings())
    print("Synthetic tenants are present. No existing tenants were changed.")


if __name__ == "__main__":
    main()
