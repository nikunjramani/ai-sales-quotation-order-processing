"""Validated configuration. Database credentials are never included in object reprs."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    # Private storage root: tenant folders with quarantined/clean attachments and quotation PDFs.
    storage_dir: Path = Path("var/storage")
    # Enquiry interpretation. "rules" is free and offline (no AI); "ollama" uses a free local
    # model. Adding a provider: see adapters/interpreters/factory.py.
    model_provider: Literal["rules", "ollama"] = "rules"
    model_name: str | None = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    model_timeout_seconds: float = 120.0
    # Portal sign-in. "dev" lets you pick a synthetic member without a password and is refused
    # in production; OIDC is added later as another provider (ADR 0013). Unset means "dev" in
    # development/test and "disabled" in production.
    auth_provider: Literal["dev", "disabled"] | None = None
    session_hours: float = Field(default=8.0, gt=0, le=24)
    # Cookies are always Secure in production; set true locally when serving over HTTPS.
    session_cookie_secure: bool = False
    # Shared secret for signed simulated-channel events (dev/test only; unset = disabled).
    simulated_channel_secret: SecretStr | None = None
    # Built React portal (portal/dist) to serve at /portal; unset = not served by the API.
    portal_dist_dir: Path | None = None

    @model_validator(mode="after")
    def no_dev_features_in_production(self) -> "Settings":
        if self.environment == "production" and (
            self.auth_provider == "dev" or self.simulated_channel_secret is not None
        ):
            raise ValueError("The dev login and simulated channel are not allowed in production")
        return self

    @property
    def portal_login(self) -> Literal["dev", "disabled"]:
        if self.auth_provider is not None:
            return self.auth_provider
        return "disabled" if self.environment == "production" else "dev"

    @property
    def cookie_secure(self) -> bool:
        return self.environment == "production" or self.session_cookie_secure

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
