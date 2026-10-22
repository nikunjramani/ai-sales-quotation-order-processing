import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from quotation_app.api.app import create_app
from quotation_app.config import Settings
from quotation_app.persistence.database import build_engine, database_ready
from quotation_app.persistence.seed import DEMO_TENANTS, seed_demo_tenants

pytestmark = pytest.mark.integration


def test_runtime_readiness(integration_settings: Settings) -> None:
    with TestClient(create_app(integration_settings)) as client:
        assert client.get("/health/ready").status_code == 200


def test_owner_is_not_a_valid_runtime_role(integration_settings: Settings) -> None:
    engine = build_engine(integration_settings.migration_url())
    try:
        assert not database_ready(engine)
    finally:
        engine.dispose()


def test_seed_idempotency_and_tenant_visibility(integration_settings: Settings) -> None:
    seed_demo_tenants(integration_settings)
    seed_demo_tenants(integration_settings)
    engine = build_engine(integration_settings.database_url.get_secret_value())
    try:
        with engine.connect() as connection:
            assert list(connection.execute(text("SELECT id FROM tenants")).scalars()) == []
        for tenant_id, _ in DEMO_TENANTS:
            with engine.begin() as connection:
                connection.execute(
                    text("SELECT set_config('app.tenant_id', :id, true)"), {"id": str(tenant_id)}
                )
                assert list(connection.execute(text("SELECT id FROM tenants")).scalars()) == [
                    tenant_id
                ]
        # A reused pooled connection cannot retain the previous transaction's tenant.
        with engine.connect() as connection:
            assert list(connection.execute(text("SELECT id FROM tenants")).scalars()) == []
        with pytest.raises(ProgrammingError), engine.begin() as connection:
            connection.execute(text("UPDATE tenants SET name = 'forbidden'"))
    finally:
        engine.dispose()
