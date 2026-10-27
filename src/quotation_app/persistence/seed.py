"""Idempotently insert fictional tenants, memberships, policies and connections (owner access).

Existing rows are left unchanged. Subjects use the reserved .example domain. Each demo business
gets one `simulated` connection (ADR 0018): the fake manager phone and its demo catalogue.
"""

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Connection, text
from sqlalchemy.dialects.postgresql import insert

from quotation_app.config import Settings
from quotation_app.domain.connections import Purpose
from quotation_app.domain.money import RoundingMode
from quotation_app.domain.tenancy import Role
from quotation_app.persistence.connections import ensure_connection
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.models import Membership, Tenant, TenantPricingPolicy

INDUSTRIAL_TENANT = UUID("11111111-1111-4111-8111-111111111111")
OFFICE_TENANT = UUID("22222222-2222-4222-8222-222222222222")

DEMO_TENANTS = (
    (INDUSTRIAL_TENANT, "Demo Industrial Supplies"),
    (OFFICE_TENANT, "Demo Office Equipment"),
)

DEMO_MEMBERSHIPS = (
    (INDUSTRIAL_TENANT, "admin@industrial.example", Role.ADMINISTRATOR),
    (INDUSTRIAL_TENANT, "sales@industrial.example", Role.SALES_OPERATOR),
    (INDUSTRIAL_TENANT, "manager@industrial.example", Role.APPROVER),
    (INDUSTRIAL_TENANT, "viewer@industrial.example", Role.VIEWER),
    (OFFICE_TENANT, "sales@office.example", Role.SALES_OPERATOR),
)

# Synthetic policies for learning; real tax/rounding rules come from each pilot business.
DEMO_POLICIES = (
    (INDUSTRIAL_TENANT, "INR", 2, RoundingMode.HALF_UP, Decimal("0.18")),
    (OFFICE_TENANT, "EUR", 2, RoundingMode.HALF_EVEN, Decimal("0.19")),
)


# The development provider (dev-only, refused in production) and its demo catalogue names.
SIMULATED_PROVIDER = "simulated"
SIMULATED_ACCOUNT = "simulated-local"
DEMO_CONNECTIONS = (
    (INDUSTRIAL_TENANT, "industrial"),
    (OFFICE_TENANT, "office"),
)


def _set_tenant(connection: Connection, tenant_id: UUID) -> None:
    # FORCE RLS also applies to the owner. Context is transaction-local.
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


def seed_demo_tenants(settings: Settings) -> None:
    if settings.environment not in {"development", "test"}:
        raise ValueError("Demo data seeding is disabled outside development/test")
    engine = build_engine(settings.migration_url())
    try:
        with engine.begin() as connection:
            for tenant_id, name in DEMO_TENANTS:
                _set_tenant(connection, tenant_id)
                connection.execute(
                    insert(Tenant)
                    .values(id=tenant_id, name=name)
                    .on_conflict_do_nothing(index_elements=["id"])
                )
            for tenant_id, subject, role in DEMO_MEMBERSHIPS:
                _set_tenant(connection, tenant_id)
                connection.execute(
                    insert(Membership)
                    .values(id=uuid4(), tenant_id=tenant_id, subject=subject, role=role.value)
                    .on_conflict_do_nothing(index_elements=["tenant_id", "subject", "role"])
                )
            for tenant_id, currency, minor_units, rounding, tax_rate in DEMO_POLICIES:
                _set_tenant(connection, tenant_id)
                connection.execute(
                    insert(TenantPricingPolicy)
                    .values(
                        tenant_id=tenant_id,
                        version=1,
                        currency=currency,
                        minor_units=minor_units,
                        rounding_mode=rounding.value,
                        tax_rate=tax_rate,
                        max_price_age_seconds=900,
                        max_stock_age_seconds=300,
                    )
                    .on_conflict_do_nothing(index_elements=["tenant_id"])
                )
            for tenant_id, catalogue in DEMO_CONNECTIONS:
                _set_tenant(connection, tenant_id)
                ensure_connection(
                    connection,
                    tenant_id=tenant_id,
                    provider_key=SIMULATED_PROVIDER,
                    account_ref=SIMULATED_ACCOUNT,
                    display_name="Simulated phone and demo catalogue",
                    purposes=[Purpose.MANAGER_APPROVALS, Purpose.CATALOGUE],
                    created_by="seed",
                    config={"catalogue": catalogue},
                )
    finally:
        engine.dispose()


def main() -> None:
    seed_demo_tenants(Settings())
    print(
        "Synthetic tenants, memberships, policies and connections are present. "
        "Existing rows unchanged."
    )


if __name__ == "__main__":
    main()
