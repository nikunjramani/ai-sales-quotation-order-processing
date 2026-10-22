"""Tenant-scoped repositories. Every query runs in a transaction with the tenant context set.

Queries also filter by tenant_id explicitly; PostgreSQL RLS is the second, independent guard.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from sqlalchemy import Connection, Engine, select, text

from quotation_app.domain.money import RoundingMode
from quotation_app.domain.pricing import PricingPolicy
from quotation_app.domain.tenancy import Role, TenantContext
from quotation_app.persistence.models import Membership, TenantPricingPolicy
from quotation_app.ports.tenancy import PricingPolicyNotConfigured


@contextmanager
def tenant_transaction(engine: Engine, tenant_id: UUID) -> Iterator[Connection]:
    """Open a transaction whose RLS tenant context ends when the transaction ends.

    set_config(..., true) is transaction-local, so a pooled connection cannot carry this
    tenant into its next checkout.
    """
    with engine.begin() as connection:
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        yield connection


class SqlMembershipReader:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def roles_for(self, tenant_id: UUID, subject: str) -> frozenset[Role]:
        with tenant_transaction(self._engine, tenant_id) as connection:
            values = connection.execute(
                select(Membership.role).where(
                    Membership.tenant_id == tenant_id, Membership.subject == subject
                )
            ).scalars()
            return frozenset(Role(value) for value in values)


class SqlPricingPolicyReader:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, context: TenantContext) -> PricingPolicy:
        table = TenantPricingPolicy
        with tenant_transaction(self._engine, context.tenant_id) as connection:
            row = connection.execute(
                select(
                    table.tenant_id,
                    table.version,
                    table.currency,
                    table.minor_units,
                    table.rounding_mode,
                    table.tax_rate,
                    table.max_price_age_seconds,
                    table.max_stock_age_seconds,
                ).where(table.tenant_id == context.tenant_id)
            ).one_or_none()
        if row is None:
            raise PricingPolicyNotConfigured("No pricing policy is configured for this tenant")
        return PricingPolicy(
            tenant_id=row.tenant_id,
            version=row.version,
            currency=row.currency,
            minor_units=row.minor_units,
            rounding=RoundingMode(row.rounding_mode),
            tax_rate=row.tax_rate,
            max_price_age=timedelta(seconds=row.max_price_age_seconds),
            max_stock_age=timedelta(seconds=row.max_stock_age_seconds),
        )
