"""Validated configuration. Database credentials are never included in object reprs."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUOTATION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    worker_database_url: SecretStr | None = None
    # Private attachment storage root; tenant folders and quarantine live underneath it.
    storage_dir: Path = Path("var/storage")
    # Enquiry interpretation. "rules" is free and offline (no AI); "ollama" uses a free local
    # model. Adding a provider: see adapters/interpreters/factory.py.
    model_provider: Literal["rules", "ollama"] = "rules"
    model_name: str | None = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    model_timeout_seconds: float = 120.0

    @field_validator("database_url", "migration_database_url", "worker_database_url")
    @classmethod
    def postgres_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("A valid PostgreSQL URL is required") from None
        if url.drivername != "postgresql+psycopg" or not url.host or not url.database:
            raise ValueError("Use postgresql+psycopg with an explicit host and database")
        return value

    def migration_url(self) -> str:
        """Explicit owner credentials are required; never fall back to the app role."""
        if self.migration_database_url is None:
            raise ValueError("QUOTATION_MIGRATION_DATABASE_URL is required for migrations/seed")
        return self.migration_database_url.get_secret_value()

    def worker_url(self) -> str:
        """The worker uses its own role; never fall back to the API or owner role."""
        if self.worker_database_url is None:
            raise ValueError("QUOTATION_WORKER_DATABASE_URL is required for the job worker")
        return self.worker_database_url.get_secret_value()
