"""Unit tests run offline; integration tests require an explicit opt-in and URLs."""

import os

import pytest
from pydantic import SecretStr

from quotation_app.config import Settings


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration", action="store_true", help="Use a disposable PostgreSQL DB"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--run-integration"):
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Pass --run-integration with test DB URLs"))


@pytest.fixture
def integration_settings() -> Settings:
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
