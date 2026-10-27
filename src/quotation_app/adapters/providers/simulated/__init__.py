"""Provider `simulated` (development only): see provider.py."""

from quotation_app.adapters.providers.simulated.provider import PROVIDER_KEY, SimulatedProvider
from quotation_app.ports.providers import ProviderEnvironment

OUTBOX_FOLDER = "simulated-channel"
# account_ref of the demo businesses' simulated connection (the seed creates it).
DEFAULT_CONNECTION_ID = "simulated-local"


def build(environment: ProviderEnvironment) -> SimulatedProvider:
    """Entry point `simulated` in group quotation_app.providers."""
    return SimulatedProvider(environment.storage_dir / OUTBOX_FOLDER)


__all__ = ["DEFAULT_CONNECTION_ID", "OUTBOX_FOLDER", "PROVIDER_KEY", "SimulatedProvider", "build"]
