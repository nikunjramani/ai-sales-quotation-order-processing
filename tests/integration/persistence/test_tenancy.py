"""Two-tenant negative tests through the real PostgreSQL runtime role (not the owner)."""

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import ProgrammingError

from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.application.pricing import QuotationPricingService
from quotation_app.application.tenancy import TenantContextResolver
from quotation_app.domain.money import Money
from quotation_app.domain.pricing import PricedQuotation, RequestedLine
from quotation_app.domain.tenancy import AccessDenied, Role, TenantContext
from quotation_app.persistence.tenancy import (
    SqlMembershipReader,
    SqlPricingPolicyReader,
    tenant_transaction,
)
from quotation_app.ports.tenancy import PricingPolicyNotConfigured

type ContextFactory = Callable[[UUID, Role], TenantContext]


def test_membership_is_scoped_to_its_tenant(
    runtime_engine: Engine, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    resolver = TenantContextResolver(SqlMembershipReader(runtime_engine))
    context = resolver.resolve("sales@industrial.example", industrial_tenant)
    assert context.roles == {Role.SALES_OPERATOR}
    # A real member of tenant A gains nothing by naming tenant B.
    with pytest.raises(AccessDenied):
        resolver.resolve("sales@industrial.example", office_tenant)
    with pytest.raises(AccessDenied):
        resolver.resolve("sales@office.example", industrial_tenant)
    with pytest.raises(AccessDenied):
        resolver.resolve("sales@industrial.example", uuid4())


@pytest.mark.parametrize("table", ["memberships", "tenant_pricing_policies"])
def test_rows_are_invisible_without_or_across_tenant_context(
    runtime_engine: Engine, office_tenant: UUID, table: str
) -> None:
    with runtime_engine.connect() as connection:
        count = connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        assert count == 0, f"{table} visible without tenant context"
    with tenant_transaction(runtime_engine, office_tenant) as connection:
        tenants = set(connection.execute(text(f"SELECT DISTINCT tenant_id FROM {table}")).scalars())
        assert tenants == {office_tenant}


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO memberships (id, tenant_id, subject, role) "
        "VALUES (gen_random_uuid(), :tenant, 'intruder@example.test', 'approver')",
        "UPDATE tenant_pricing_policies SET tax_rate = 0 WHERE tenant_id = :tenant",
    ],
)
def test_runtime_role_cannot_change_access_or_policy(
    runtime_engine: Engine, industrial_tenant: UUID, statement: str
) -> None:
    with (
        pytest.raises(ProgrammingError),
        tenant_transaction(runtime_engine, industrial_tenant) as connection,
    ):
        connection.execute(text(statement), {"tenant": industrial_tenant})


def test_policies_are_read_per_tenant(
    runtime_engine: Engine,
    make_context: ContextFactory,
    industrial_tenant: UUID,
    office_tenant: UUID,
) -> None:
    reader = SqlPricingPolicyReader(runtime_engine)
    industrial = reader.get(make_context(industrial_tenant, Role.VIEWER))
    office = reader.get(make_context(office_tenant, Role.VIEWER))
    assert (industrial.currency, industrial.tax_rate) == ("INR", Decimal("0.180000"))
    assert (office.currency, office.tax_rate) == ("EUR", Decimal("0.190000"))
    with pytest.raises(PricingPolicyNotConfigured):
        reader.get(make_context(uuid4(), Role.VIEWER))


def test_end_to_end_pricing_with_database_policy(
    runtime_engine: Engine, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    resolver = TenantContextResolver(SqlMembershipReader(runtime_engine))
    service = QuotationPricingService(
        SimulatedErp(demo_catalogues(industrial_tenant, office_tenant)),
        SqlPricingPolicyReader(runtime_engine),
    )
    context = resolver.resolve("sales@industrial.example", industrial_tenant)
    outcome = service.price(context, [RequestedLine("IND-BOLT-M8", Decimal(100), "each")])
    assert isinstance(outcome, PricedQuotation)
    assert outcome.total == Money(Decimal("280.25"), "INR")
