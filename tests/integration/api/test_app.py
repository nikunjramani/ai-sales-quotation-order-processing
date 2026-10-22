from fastapi.testclient import TestClient
from sqlalchemy import Engine

from quotation_app.api.app import create_app
from quotation_app.config import Settings


def test_readiness_with_real_database(
    integration_settings: Settings, runtime_engine: Engine
) -> None:
    with TestClient(create_app(integration_settings)) as client:
        assert client.get("/health/ready").json() == {"status": "ready"}
