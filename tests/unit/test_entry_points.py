"""The installed package metadata registers the in-repo pluggable parts (run `uv sync`)."""

from importlib.metadata import entry_points

from quotation_app.composition import build_secret_store
from quotation_app.config import Settings


def test_providers_are_registered() -> None:
    names = {entry.name for entry in entry_points(group="quotation_app.providers")}
    assert {"api", "simulated"} <= names


def test_secret_stores_are_registered() -> None:
    names = {entry.name for entry in entry_points(group="quotation_app.secret_stores")}
    assert {"local", "none"} <= names


def test_production_gets_the_none_store() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://app:x@localhost/db",
        environment="production",
        mailer="real_mailer",
        mail_from="no-reply@quotes.example",
        public_portal_url="https://quotes.example/portal/",
    )
    assert type(build_secret_store(settings)).__name__ == "NoSecretStore"
