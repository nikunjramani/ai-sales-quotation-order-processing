"""Composition root: builds the pluggable runtime parts from settings (ADR 0018).

The API, the worker, scripts and tests all wire providers and stores through these functions,
so adding a provider never means editing the API or the worker.
"""

import threading
from collections.abc import Callable
from typing import cast
from uuid import UUID

from quotation_app.application.plugins import load_named
from quotation_app.application.providers import ProviderRegistry
from quotation_app.config import Settings
from quotation_app.ports.providers import ProviderEnvironment
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


class LazySecretStore:
    """Builds the configured store on first use.

    The API and worker start even when no store is configured (e.g. no local key); only an
    operation that really needs a secret fails, with the store's own clear error.
    """

    def __init__(self, build: Callable[[], SecretStore]) -> None:
        self._build = build
        self._store: SecretStore | None = None
        self._lock = threading.Lock()

    def _get(self) -> SecretStore:
        with self._lock:
            if self._store is None:
                self._store = self._build()
            return self._store

    def put(self, tenant_id: UUID, name: str, value: str) -> str:
        return self._get().put(tenant_id, name, value)

    def get(self, tenant_id: UUID, reference: str) -> str:
        return self._get().get(tenant_id, reference)

    def delete(self, tenant_id: UUID, reference: str) -> None:
        self._get().delete(tenant_id, reference)


def lazy_secret_store(settings: Settings) -> SecretStore:
    return LazySecretStore(lambda: build_secret_store(settings))


def build_provider_registry(settings: Settings) -> ProviderRegistry:
    return ProviderRegistry.load(
        ProviderEnvironment(environment=settings.environment, storage_dir=settings.storage_dir)
    )
