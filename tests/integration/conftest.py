"""Fixtures for tests that need a real, disposable PostgreSQL database."""

import os
from collections.abc import Iterator

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine

from quotation_app.config import Settings
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.seed import seed_demo_tenants


@pytest.fixture
def integration_settings() -> Settings:
    """Settings built only from explicit TEST_* URLs, never from a developer's .env."""
    app = os.environ.get("TEST_DATABASE_URL")
    owner = os.environ.get("TEST_MIGRATION_DATABASE_URL")
    if not app or not owner:
        pytest.fail("TEST_DATABASE_URL and TEST_MIGRATION_DATABASE_URL are required")
    return Settings(
        _env_file=None,
        environment="test",
        database_url=SecretStr(app),
        migration_database_url=SecretStr(owner),
    )


@pytest.fixture
def owner_engine(integration_settings: Settings) -> Iterator[Engine]:
    engine = build_engine(integration_settings.migration_url())
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def runtime_engine(integration_settings: Settings) -> Iterator[Engine]:
    """Restricted application role, with the synthetic seed data present."""
    seed_demo_tenants(integration_settings)
    engine = build_engine(integration_settings.database_url.get_secret_value())
    try:
        yield engine
    finally:
        engine.dispose()
