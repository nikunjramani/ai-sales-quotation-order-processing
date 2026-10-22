from fastapi.testclient import TestClient
from pydantic import SecretStr
from pytest import MonkeyPatch
from sqlalchemy.exc import OperationalError

from quotation_app.api.app import create_app
from quotation_app.config import Settings


def client() -> TestClient:
    settings = Settings(
        _env_file=None, database_url=SecretStr("postgresql+psycopg://app:private@localhost/db")
    )
    return TestClient(create_app(settings))


def test_liveness_does_not_need_database(monkeypatch: MonkeyPatch) -> None:
    def forbidden(*args: object) -> bool:
        raise AssertionError("Liveness must not query the database")

    monkeypatch.setattr("quotation_app.api.app.database_ready", forbidden)
    with client() as http:
        assert http.get("/health/live").json() == {"status": "ok"}


def test_readiness_failure_is_sanitized(monkeypatch: MonkeyPatch) -> None:
    def unavailable(*args: object) -> bool:
        raise OperationalError("private connection info", {}, Exception("password=private"))

    monkeypatch.setattr("quotation_app.api.app.database_ready", unavailable)
    with client() as http:
        response = http.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready"}
        assert "private" not in response.text


def test_readiness_requires_valid_schema_and_role(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("quotation_app.api.app.database_ready", lambda _: False)
    with client() as http:
        assert http.get("/health/ready").status_code == 503
    monkeypatch.setattr("quotation_app.api.app.database_ready", lambda _: True)
    with client() as http:
        assert http.get("/health/ready").json() == {"status": "ready"}
