import pytest
from pydantic import SecretStr, ValidationError

from quotation_app.config import Settings
from quotation_app.persistence.seed import seed_demo_tenants


def test_settings_require_postgres_and_hide_credentials() -> None:
    settings = Settings(
        _env_file=None, database_url=SecretStr("postgresql+psycopg://app:private@localhost/db")
    )
    assert "private" not in repr(settings)
    with pytest.raises(ValidationError, match="postgresql"):
        Settings(_env_file=None, database_url=SecretStr("sqlite:///example.db"))


def test_missing_migration_url_has_no_runtime_fallback() -> None:
    settings = Settings(
        _env_file=None,
        database_url=SecretStr("postgresql+psycopg://app:private@localhost/db"),
        migration_database_url=None,
    )
    with pytest.raises(ValueError, match="MIGRATION_DATABASE_URL"):
        settings.migration_url()


def test_production_seed_is_rejected_before_connecting() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url=SecretStr("postgresql+psycopg://app:private@localhost/db"),
    )
    with pytest.raises(ValueError, match="disabled"):
        seed_demo_tenants(settings)
