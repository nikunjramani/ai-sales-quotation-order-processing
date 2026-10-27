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


def test_ai_model_is_generic_and_its_key_stays_hidden() -> None:
    settings = Settings(
        _env_file=None,
        database_url=RUNTIME_URL,
        model="google_genai:gemini-3.5-flash-lite",
        model_api_key=SecretStr("synthetic-model-key"),
        model_options={"timeout": 30},
    )
    assert "synthetic-model-key" not in repr(settings)
    assert Settings(_env_file=None, database_url=RUNTIME_URL).model is None  # rules, no AI
    with pytest.raises(ValidationError, match="model"):
        Settings(_env_file=None, database_url=RUNTIME_URL, model="gemini-3.5-flash-lite")


def test_secret_store_defaults_and_production_rule() -> None:
    development = Settings(_env_file=None, database_url=RUNTIME_URL)
    assert development.secret_store_name == "local"
    production = Settings(_env_file=None, database_url=RUNTIME_URL, environment="production")
    assert production.secret_store_name == "none"
    with pytest.raises(ValidationError, match="local secret store"):
        Settings(
            _env_file=None, database_url=RUNTIME_URL, environment="production", secret_store="local"
        )
    keyed = Settings(
        _env_file=None, database_url=RUNTIME_URL, secret_store_key=SecretStr("synthetic-key")
    )
    assert "synthetic-key" not in repr(keyed)
