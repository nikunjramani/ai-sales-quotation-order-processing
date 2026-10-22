"""Shared ERP contract suite: every ERP adapter must pass these tests.

To add an adapter, register a factory in ADAPTERS. Each factory returns the adapter, two
tenant contexts and a SKU that exists only for the first tenant. A real adapter that needs a
sandbox registers with `pytest.param(..., marks=pytest.mark.integration)` so it is skipped
unless --run-integration is passed.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest

from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.domain.tenancy import Role, TenantContext
from quotation_app.persistence.seed import INDUSTRIAL_TENANT, OFFICE_TENANT
from quotation_app.ports.erp import ErpReader


@dataclass(frozen=True)
class ContractSetup:
    erp: ErpReader
    tenant: TenantContext
    other_tenant: TenantContext
    known_sku: str
    currency: str


def _context(tenant_id: UUID) -> TenantContext:
    return TenantContext(tenant_id, "contract@example.test", frozenset({Role.SALES_OPERATOR}))


def _simulated() -> ContractSetup:
    return ContractSetup(
        erp=SimulatedErp(demo_catalogues(INDUSTRIAL_TENANT, OFFICE_TENANT)),
        tenant=_context(INDUSTRIAL_TENANT),
        other_tenant=_context(OFFICE_TENANT),
        known_sku="IND-FAN-450",
        currency="INR",
    )


ADAPTERS: list[object] = [pytest.param(_simulated, id="simulated")]


@pytest.fixture(params=ADAPTERS)
def setup(request: pytest.FixtureRequest) -> ContractSetup:
    factory: Callable[[], ContractSetup] = request.param
    return factory()


def test_known_sku_returns_evidence(setup: ContractSetup) -> None:
    erp, tenant, sku = setup.erp, setup.tenant, setup.known_sku
    now = datetime.now(UTC)
    assert set(erp.get_products(tenant, [sku])) == {sku}
    price = erp.get_prices(tenant, [sku], setup.currency, now)[sku]
    assert price.unit_price.currency == setup.currency
    assert price.unit_price.amount >= 0
    assert price.is_effective_at(now)
    assert price.source and price.fetched_at.tzinfo is not None
    level = erp.get_availability(tenant, [sku])[sku]
    assert level.source and level.fetched_at.tzinfo is not None


def test_unknown_sku_is_absent_not_zero(setup: ContractSetup) -> None:
    erp, tenant, unknown = setup.erp, setup.tenant, "CONTRACT-UNKNOWN-SKU"
    assert erp.get_products(tenant, [unknown]) == {}
    assert erp.get_prices(tenant, [unknown], setup.currency, datetime.now(UTC)) == {}
    assert erp.get_availability(tenant, [unknown]) == {}


def test_other_tenant_cannot_see_records(setup: ContractSetup) -> None:
    erp, other, sku = setup.erp, setup.other_tenant, setup.known_sku
    assert erp.get_products(other, [sku]) == {}
    assert erp.get_prices(other, [sku], setup.currency, datetime.now(UTC)) == {}
    assert erp.get_availability(other, [sku]) == {}
    assert all(product.sku != sku for product in erp.search_products(other, sku))


def test_search_is_tenant_scoped(setup: ContractSetup) -> None:
    results = setup.erp.search_products(setup.tenant, setup.known_sku)
    assert setup.known_sku in {product.sku for product in results}


def test_naive_effective_date_is_rejected(setup: ContractSetup) -> None:
    with pytest.raises(ValueError, match="timezone"):
        setup.erp.get_prices(
            setup.tenant, [setup.known_sku], setup.currency, datetime(2026, 10, 22)
        )
