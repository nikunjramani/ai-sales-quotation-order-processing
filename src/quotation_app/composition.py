"""Composition root: builds the pluggable runtime parts from settings (ADR 0018).

The API, the worker, scripts and tests all wire providers and stores through these functions,
so adding a provider never means editing the API or the worker.
"""

from collections.abc import Callable
from typing import cast

from quotation_app.application.plugins import load_named
from quotation_app.config import Settings
from quotation_app.ports.secrets import SecretStore, SecretStoreEnvironment

SECRET_STORES = "quotation_app.secret_stores"


def build_secret_store(settings: Settings) -> SecretStore:
    factory = cast(
        Callable[[SecretStoreEnvironment], SecretStore],
        load_named(SECRET_STORES, settings.secret_store_name),
    )
    key = settings.secret_store_key
    return factory(
        SecretStoreEnvironment(
            environment=settings.environment,
            storage_dir=settings.storage_dir,
            key=key.get_secret_value() if key is not None else None,
            options=settings.secret_store_options,
        )
    )
