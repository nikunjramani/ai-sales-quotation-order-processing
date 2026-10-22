"""Shared test configuration and fixtures for every test folder.

Layout: tests/unit mirrors src/quotation_app and runs offline. Every test under
tests/integration is marked `integration` automatically and runs only with --run-integration
plus explicit database URLs (see tests/integration/conftest.py).
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.domain.money import RoundingMode
from quotation_app.domain.pricing import PricingPolicy
from quotation_app.domain.tenancy import Role, TenantContext
from quotation_app.persistence.seed import INDUSTRIAL_TENANT, OFFICE_TENANT
from quotation_app.ports.tenancy import PricingPolicyNotConfigured

INTEGRATION_DIR = Path(__file__).parent / "integration"

type ContextFactory = Callable[[UUID, Role], TenantContext]
type PolicyFactory = Callable[[UUID, str], PricingPolicy]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration", action="store_true", help="Use a disposable PostgreSQL DB"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_integration = config.getoption("--run-integration")
    skip = pytest.mark.skip(reason="Pass --run-integration with test DB URLs")
    for item in items:
        if item.path.is_relative_to(INTEGRATION_DIR):
            item.add_marker(pytest.mark.integration)
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip)


class FakeMemberships:
    """In-memory MembershipReader. Tests add rows: {(tenant_id, subject): roles}."""

    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str], frozenset[Role]] = {}

    def roles_for(self, tenant_id: UUID, subject: str) -> frozenset[Role]:
        return self.rows.get((tenant_id, subject), frozenset())


class FakePolicies:
    """In-memory PricingPolicyReader keyed by tenant. Tests may replace or remove entries."""

    def __init__(self, policies: dict[UUID, PricingPolicy]) -> None:
        self.policies = policies

    def get(self, context: TenantContext) -> PricingPolicy:
        try:
            return self.policies[context.tenant_id]
        except KeyError:
            raise PricingPolicyNotConfigured("No pricing policy for this tenant") from None


@pytest.fixture
def now() -> datetime:
    """The fixed 'current time' used by clocks in unit tests."""
    return datetime(2026, 10, 22, 10, 0, tzinfo=UTC)


@pytest.fixture
def industrial_tenant() -> UUID:
    return INDUSTRIAL_TENANT


@pytest.fixture
def office_tenant() -> UUID:
    return OFFICE_TENANT


@pytest.fixture
def make_context() -> ContextFactory:
    def build(tenant_id: UUID, role: Role) -> TenantContext:
        return TenantContext(tenant_id, f"{role}@example.test", frozenset({role}))

    return build


@pytest.fixture
def make_policy() -> PolicyFactory:
    """Synthetic policy: 2 decimals, half_up, 18% tax, 15 min price and 5 min stock age."""

    def build(tenant_id: UUID, currency: str) -> PricingPolicy:
        return PricingPolicy(
            tenant_id=tenant_id,
            version=1,
            currency=currency,
            minor_units=2,
            rounding=RoundingMode.HALF_UP,
            tax_rate=Decimal("0.18"),
            max_price_age=timedelta(minutes=15),
            max_stock_age=timedelta(minutes=5),
        )

    return build


@pytest.fixture
def simulated_erp(now: datetime, industrial_tenant: UUID, office_tenant: UUID) -> SimulatedErp:
    """Demo catalogues for both tenants, with the ERP clock fixed at `now`."""
    return SimulatedErp(demo_catalogues(industrial_tenant, office_tenant), clock=lambda: now)


@pytest.fixture
def membership_reader() -> FakeMemberships:
    return FakeMemberships()


@pytest.fixture
def policy_reader(
    make_policy: PolicyFactory, industrial_tenant: UUID, office_tenant: UUID
) -> FakePolicies:
    return FakePolicies(
        {
            industrial_tenant: make_policy(industrial_tenant, "INR"),
            office_tenant: make_policy(office_tenant, "EUR"),
        }
    )
