"""HTTP contract of the enquiry API, using the real router and services over in-memory fakes."""

import base64
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from quotation_app.api.enquiries import MAX_REQUEST_BYTES, build_enquiry_router
from quotation_app.application.api_keys import ApiKeyAuthenticator, generate_api_key
from quotation_app.application.intake import EnquiryIntakeService
from quotation_app.domain.tenancy import Role
from quotation_app.ports.api_keys import ApiKeyRecord

BODY = {"text": "Please quote 50 industrial fans for Pune", "customer_reference": "CUST-1"}


@pytest.fixture
def client(
    api_key_reader: Any, intake_store: Any, memory_storage: Any, now: datetime
) -> Iterator[TestClient]:
    app = FastAPI()
    intake = EnquiryIntakeService(intake_store, memory_storage, clock=lambda: now)
    app.include_router(build_enquiry_router(ApiKeyAuthenticator(api_key_reader), intake))
    with TestClient(app) as http:
        yield http


@pytest.fixture
def make_headers(api_key_reader: Any) -> Any:
    def build(
        tenant: UUID, role: Role = Role.INTAKE_SERVICE, key: str = "req-000001"
    ) -> dict[str, str]:
        new = generate_api_key()
        api_key_reader.records[new.key_id] = ApiKeyRecord(
            new.key_id, tenant, role, new.secret_sha256, False
        )
        return {"Authorization": f"Bearer {new.token}", "Idempotency-Key": key}

    return build


def test_accept_then_replay_then_conflict(
    client: TestClient, make_headers: Any, industrial_tenant: UUID
) -> None:
    headers = make_headers(industrial_tenant)
    first = client.post("/api/v1/enquiries", json=BODY, headers=headers)
    assert first.status_code == 202
    accepted = first.json()
    assert accepted["status"] == "received" and accepted["duplicate"] is False
    assert first.headers["X-Correlation-ID"] == accepted["correlation_id"]

    replay = client.post("/api/v1/enquiries", json=BODY, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == {**accepted, "duplicate": True}

    changed = client.post("/api/v1/enquiries", json={**BODY, "text": "other"}, headers=headers)
    assert changed.status_code == 409


def test_status_lookup_is_tenant_scoped(
    client: TestClient, make_headers: Any, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    attachment = {
        "filename": "spec.txt",
        "content_type": "text/plain",
        "content_base64": base64.b64encode(b"50 fans, 450 mm").decode(),
    }
    created = client.post(
        "/api/v1/enquiries",
        json={**BODY, "attachments": [attachment]},
        headers=make_headers(industrial_tenant),
    ).json()
    url = f"/api/v1/enquiries/{created['enquiry_id']}"
    own = client.get(url, headers=make_headers(industrial_tenant, Role.VIEWER))
    assert own.status_code == 200
    assert own.json()["attachments"][0]["status"] == "quarantined"
    assert client.get(url, headers=make_headers(office_tenant, Role.VIEWER)).status_code == 404


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer qk_bad", "Basic dXNlcjpwYXNz", "Bearer " + "qk_" + "0" * 32 + "_x"],
)
def test_bad_credentials_get_401(client: TestClient, authorization: str | None) -> None:
    headers = {"Idempotency-Key": "req-000001"}
    if authorization:
        headers["Authorization"] = authorization
    response = client.post("/api/v1/enquiries", json=BODY, headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_tenant_field_in_body_is_rejected_not_trusted(
    client: TestClient, make_headers: Any, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    body = {**BODY, "tenant_id": str(office_tenant)}
    response = client.post("/api/v1/enquiries", json=body, headers=make_headers(industrial_tenant))
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"text": ""}, 422),
        (
            {
                "attachments": [
                    {
                        "filename": "a.pdf",
                        "content_type": "application/pdf",
                        "content_base64": "not base64!",
                    }
                ]
            },
            422,
        ),
        ({}, 403),
    ],
)
def test_validation_and_permission_errors(
    client: TestClient,
    make_headers: Any,
    industrial_tenant: UUID,
    change: dict[str, object],
    expected: int,
) -> None:
    role = Role.VIEWER if expected == 403 else Role.INTAKE_SERVICE
    response = client.post(
        "/api/v1/enquiries", json={**BODY, **change}, headers=make_headers(industrial_tenant, role)
    )
    assert response.status_code == expected


def test_missing_or_short_idempotency_key(
    client: TestClient, make_headers: Any, industrial_tenant: UUID
) -> None:
    headers = make_headers(industrial_tenant)
    del headers["Idempotency-Key"]
    assert client.post("/api/v1/enquiries", json=BODY, headers=headers).status_code == 422
    headers["Idempotency-Key"] = "short"
    assert client.post("/api/v1/enquiries", json=BODY, headers=headers).status_code == 422


def test_oversized_request_is_refused_before_parsing(
    client: TestClient, make_headers: Any, industrial_tenant: UUID
) -> None:
    headers = {
        **make_headers(industrial_tenant),
        "Content-Length": str(MAX_REQUEST_BYTES + 1),
        "Content-Type": "application/json",
    }
    response = client.post("/api/v1/enquiries", content=b"{}", headers=headers)
    assert response.status_code == 413


def test_storage_failure_is_503_and_nothing_is_accepted(
    client: TestClient, make_headers: Any, industrial_tenant: UUID, intake_store: Any
) -> None:
    intake_store.fail_record = OperationalError("insert", {}, Exception("connection lost"))
    response = client.post("/api/v1/enquiries", json=BODY, headers=make_headers(industrial_tenant))
    assert response.status_code == 503
    assert "retry with the same Idempotency-Key" in response.json()["detail"]
    assert intake_store.receipts == {}
