import pytest
from pydantic import SecretStr, ValidationError

from quotation_app.config import Settings

RUNTIME_URL = SecretStr("postgresql+psycopg://app:private@localhost/db")


def test_settings_require_postgres_and_hide_credentials() -> None:
    settings = Settings(_env_file=None, database_url=RUNTIME_URL)
    assert "private" not in repr(settings)
    with pytest.raises(ValidationError, match="postgresql"):
        Settings(_env_file=None, database_url=SecretStr("sqlite:///example.db"))


def test_missing_migration_url_has_no_runtime_fallback() -> None:
    settings = Settings(_env_file=None, database_url=RUNTIME_URL, migration_database_url=None)
    with pytest.raises(ValueError, match="MIGRATION_DATABASE_URL"):
        settings.migration_url()
