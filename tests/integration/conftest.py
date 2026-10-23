"""Fixtures for tests that need a real, disposable PostgreSQL database.

Safety: these tests clear intake and job tables, so they refuse to run unless every TEST_*
URL points at a database whose name ends in `_test`. scripts/check_database.py supplies them.
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

from quotation_app.adapters.storage.local import LocalObjectStorage
from quotation_app.application.api_keys import generate_api_key
from quotation_app.config import Settings
from quotation_app.domain.tenancy import Role
from quotation_app.persistence.api_keys import insert_api_key
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.seed import seed_demo_tenants

type ApiKeyFactory = Callable[[UUID, Role], str]

_INTAKE_TABLES = (
    "approval_action_refs, channel_bindings, channel_enrollments, approval_decisions, "
    "approval_tasks, quotation_versions, quotations, user_sessions, "
    "checkpoint_writes, checkpoint_blobs, checkpoints, workflow_runs, "
    "jobs, attachments, enquiries, inbox_events, api_keys"
)


def _required_test_url(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.fail(f"{name} is required for integration tests")
    if not (make_url(value).database or "").endswith("_test"):
        pytest.fail(f"{name} must point at a *_test database; integration tests clear tables")
    return value


@pytest.fixture
def integration_settings(tmp_path: Path) -> Settings:
    """Settings built only from explicit TEST_* URLs, never from a developer's .env."""
    return Settings(
        _env_file=None,
        environment="test",
        database_url=SecretStr(_required_test_url("TEST_DATABASE_URL")),
        migration_database_url=SecretStr(_required_test_url("TEST_MIGRATION_DATABASE_URL")),
        worker_database_url=SecretStr(_required_test_url("TEST_WORKER_DATABASE_URL")),
        storage_dir=tmp_path / "storage",
    )


@pytest.fixture
def owner_engine(integration_settings: Settings) -> Iterator[Engine]:
    engine = build_engine(integration_settings.migration_url())
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_intake_tables(owner_engine: Engine) -> None:
    """Each test starts with empty intake/job tables (TRUNCATE is owner-only, bypassing RLS)."""
    with owner_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {_INTAKE_TABLES}"))


@pytest.fixture
def runtime_engine(integration_settings: Settings) -> Iterator[Engine]:
    """Restricted API role, with the synthetic seed data present."""
    seed_demo_tenants(integration_settings)
    engine = build_engine(integration_settings.database_url.get_secret_value())
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def worker_engine(integration_settings: Settings, runtime_engine: Engine) -> Iterator[Engine]:
    """Worker role: sees the job queue across tenants, everything else only with context."""
    engine = build_engine(integration_settings.worker_url())
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def storage(integration_settings: Settings) -> LocalObjectStorage:
    return LocalObjectStorage(integration_settings.storage_dir)


@pytest.fixture
def make_api_key(owner_engine: Engine, runtime_engine: Engine) -> ApiKeyFactory:
    """Create a key for a tenant/role and return its bearer token."""

    def create(tenant_id: UUID, role: Role) -> str:
        key = generate_api_key()
        insert_api_key(owner_engine, key.key_id, tenant_id, f"test {role}", role, key.secret_sha256)
        return key.token

    return create
