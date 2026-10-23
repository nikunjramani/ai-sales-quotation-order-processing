"""HTTP contract of portal sign-in, quotation/approval routes and the simulated channel webhook.

Real routers and services over the in-memory fakes; tests/integration repeats the key flows on
PostgreSQL.
"""

import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from quotation_app.adapters.channels.simulated import SIGNATURE_HEADER, sign
from quotation_app.adapters.identity.dev import DevIdentityProvider
from quotation_app.api.auth import CSRF_HEADER, SESSION_COOKIE, PortalAuth, build_auth_router
from quotation_app.api.channels import build_channel_router
from quotation_app.api.portal import build_portal_router
from quotation_app.application.intake import EnquiryListService
from quotation_app.application.sessions import SessionService
from quotation_app.application.tenancy import TenantContextResolver
from quotation_app.domain.quotations import ApprovalAction

MANAGER = "manager@industrial.example"
SALES = "sales@industrial.example"
SECRET = "unit-test-channel-secret"


class NoEnquiries:
    def list_enquiries(self, tenant_id: UUID, statuses: object, limit: int) -> list[Any]:
        return []


def build_app(harness: Any, sessions: Any, directory: Any, dev: bool = True) -> FastAPI:
    auth = PortalAuth(SessionService(sessions), TenantContextResolver(harness.db))
    app = FastAPI()
    app.include_router(
        build_auth_router(
            auth, directory, DevIdentityProvider(directory) if dev else None, [MANAGER], False
        )
    )
    app.include_router(
        build_portal_router(
            auth,
            harness.quotations,
            harness.approvals,
            harness.channels,
            EnquiryListService(NoEnquiries()),
            clock=harness.clock,
        )
    )
    app.include_router(build_channel_router(harness.channels, SECRET))
    return app


@pytest.fixture
def client(harness: Any, memory_sessions: Any, memory_directory: Any) -> Iterator[TestClient]:
    with TestClient(build_app(harness, memory_sessions, memory_directory)) as http:
        yield http


def login(client: TestClient, subject: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/dev-login", json={"subject": subject})
    assert response.status_code == 200, response.text
    return {CSRF_HEADER: response.json()["csrf_token"]}


@pytest.fixture
def pending(harness: Any) -> tuple[UUID, Any]:
    enquiry = harness.enquiry(("IND-FAN-450", "2", "each"))
    harness.run_jobs()
    return harness.quotation(enquiry).quotation_id, harness.pending_task(enquiry)


def base(harness: Any) -> str:
    return f"/api/v1/tenants/{harness.tenant_id}"


def test_dev_login_sets_a_protected_cookie_and_returns_tenants(
    client: TestClient, harness: Any
) -> None:
    assert client.get("/api/v1/auth/config").json() == {
        "provider": "dev",
        "dev_subjects": [MANAGER],
    }
    response = client.post("/api/v1/auth/dev-login", json={"subject": MANAGER})
    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE}=" in cookie
    for flag in ("HttpOnly", "SameSite=strict", "Path=/api"):
        assert flag.lower() in cookie.lower()
    body = response.json()
    assert body["subject"] == MANAGER and len(body["csrf_token"]) == 64
    assert body["tenants"][0]["roles"] == ["approver"]
    assert "quotations:approve" in body["tenants"][0]["permissions"]
    assert client.get("/api/v1/auth/session").json()["csrf_token"] == body["csrf_token"]


def test_unknown_people_and_disabled_dev_login_are_refused(
    harness: Any, memory_sessions: Any, memory_directory: Any
) -> None:
    with TestClient(build_app(harness, memory_sessions, memory_directory)) as http:
        assert (
            http.post("/api/v1/auth/dev-login", json={"subject": "nobody@x.test"}).status_code
            == 401
        )
        assert http.get("/api/v1/auth/session").status_code == 401
    with TestClient(build_app(harness, memory_sessions, memory_directory, dev=False)) as http:
        assert http.get("/api/v1/auth/config").json()["provider"] == "disabled"
        assert http.post("/api/v1/auth/dev-login", json={"subject": MANAGER}).status_code == 404


def test_changes_need_the_csrf_header_and_logout_ends_the_session(
    client: TestClient, harness: Any, pending: tuple[UUID, Any]
) -> None:
    headers = login(client, MANAGER)
    _, task = pending
    body = {
        "command_id": str(uuid4()),
        "action": "approve",
        "content_sha256": task.content_sha256,
    }
    url = f"{base(harness)}/approval-tasks/{task.task_id}/decision"
    assert client.post(url, json=body).status_code == 403
    assert client.post(url, json=body, headers={CSRF_HEADER: "0" * 64}).status_code == 403
    assert client.post("/api/v1/auth/logout").status_code == 403
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/session").status_code == 401


def test_non_members_get_not_found(client: TestClient, office_tenant: UUID) -> None:
    login(client, MANAGER)
    assert client.get(f"/api/v1/tenants/{office_tenant}/quotations").status_code == 404
    assert client.get(f"/api/v1/tenants/{uuid4()}/quotations").status_code == 404


def test_manager_reviews_and_approves_with_replay_and_conflict(
    client: TestClient, harness: Any, pending: tuple[UUID, Any]
) -> None:
    quotation_id, task = pending
    headers = login(client, MANAGER)
    listed = client.get(f"{base(harness)}/quotations", params={"status": "pending_approval"})
    assert [item["quotation_id"] for item in listed.json()] == [str(quotation_id)]
    assert listed.json()[0]["total"] == "10030.00"
    detail = client.get(f"{base(harness)}/quotations/{quotation_id}").json()
    assert detail["can_decide"] is True and detail["can_revise"] is False
    assert detail["pending_task"]["task_id"] == str(task.task_id)
    assert detail["versions"][0]["content"]["lines"][0]["sku"] == "IND-FAN-450"

    url = f"{base(harness)}/approval-tasks/{task.task_id}/decision"
    stale = {"command_id": str(uuid4()), "action": "approve", "content_sha256": "c" * 64}
    assert client.post(url, json=stale, headers=headers).status_code == 409
    body = {**stale, "content_sha256": detail["pending_task"]["content_sha256"]}
    first = client.post(url, json=body, headers=headers)
    assert first.status_code == 200 and first.json()["replayed"] is False
    assert client.post(url, json=body, headers=headers).json()["replayed"] is True
    other = {**body, "command_id": str(uuid4()), "action": "reject", "reason": "late"}
    conflict = client.post(url, json=other, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["decision"]["action"] == "approve"
    missing_reason = {**other, "reason": None}
    assert client.post(url, json=missing_reason, headers=headers).status_code == 422


def test_sales_cannot_decide_but_can_revise_when_asked(
    client: TestClient, harness: Any, pending: tuple[UUID, Any]
) -> None:
    quotation_id, task = pending
    headers = login(client, SALES)
    decision = {
        "command_id": str(uuid4()),
        "action": "approve",
        "content_sha256": task.content_sha256,
    }
    url = f"{base(harness)}/approval-tasks/{task.task_id}/decision"
    assert client.post(url, json=decision, headers=headers).status_code == 403
    harness.approvals.decide(MANAGER, harness.command(task, ApprovalAction.REQUEST_REVISION, "qty"))
    harness.run_jobs()
    assert client.get(f"{base(harness)}/quotations/{quotation_id}").json()["can_revise"] is True
    revise = f"{base(harness)}/quotations/{quotation_id}/revisions"
    unpriced = {
        "command_id": str(uuid4()),
        "base_version": 1,
        "lines": [{"sku": "IND-PUMP-2HP", "quantity": "1", "unit": "each"}],
        "reason": "pump",
    }
    rejected = client.post(revise, json=unpriced, headers=headers)
    assert rejected.status_code == 422 and rejected.json()["issues"][0]["code"] == "price_missing"
    bad = {**unpriced, "lines": [{"sku": "IND-FAN-450", "quantity": "lots", "unit": "each"}]}
    assert client.post(revise, json=bad, headers=headers).status_code == 422
    good = {**unpriced, "lines": [{"sku": "IND-FAN-450", "quantity": "3", "unit": "each"}]}
    created = client.post(revise, json=good, headers=headers)
    assert created.status_code == 201 and created.json()["version"] == 2
    assert client.post(revise, json=good, headers=headers).status_code == 200  # replay
    stale = {**good, "command_id": str(uuid4())}
    assert client.post(revise, json=stale, headers=headers).status_code == 409


def test_channel_linking_through_portal_and_signed_webhook(
    client: TestClient, harness: Any
) -> None:
    headers = login(client, MANAGER)
    code = client.post(
        f"{base(harness)}/channel-enrollments", json={"channel": "simulated"}, headers=headers
    ).json()["code"]
    event = {
        "event_id": "evt-1",
        "tenant_id": str(harness.tenant_id),
        "connection_id": "simulated-local",
        "external_user_id": "phone-manager",
        "type": "enroll",
        "code": code,
    }
    raw = json.dumps(event).encode()
    url = "/api/v1/channels/simulated/events"
    assert client.post(url, content=raw).status_code == 401
    assert client.post(url, content=raw, headers={SIGNATURE_HEADER: "0" * 64}).status_code == 401
    tampered = raw.replace(b"phone-manager", b"phone-attacker")
    assert (
        client.post(
            url, content=tampered, headers={SIGNATURE_HEADER: sign(SECRET, raw)}
        ).status_code
        == 401
    )
    enrolled = client.post(url, content=raw, headers={SIGNATURE_HEADER: sign(SECRET, raw)})
    assert enrolled.status_code == 200 and enrolled.json()["result"] == "enrolled"
    bindings = client.get(f"{base(harness)}/channel-bindings").json()
    assert [item["external_user_id"] for item in bindings] == ["phone-manager"]

    harness.enquiry(("IND-FAN-450", "2", "each"))
    harness.run_jobs()
    reference = harness.notifier.sent[0][2]
    decision = {**event, "event_id": "evt-2", "type": "decision", "code": None,
                "action_reference": reference, "action": "approve"}  # fmt: skip
    raw = json.dumps(decision).encode()
    recorded = client.post(url, content=raw, headers={SIGNATURE_HEADER: sign(SECRET, raw)})
    assert recorded.json()["result"] == "recorded"
    replay = client.post(url, content=raw, headers={SIGNATURE_HEADER: sign(SECRET, raw)})
    assert replay.json()["result"] == "replayed"
    forged = json.dumps({**decision, "event_id": "evt-3", "external_user_id": "other"}).encode()
    assert (
        client.post(
            url, content=forged, headers={SIGNATURE_HEADER: sign(SECRET, forged)}
        ).status_code
        == 403
    )

    revoke = client.delete(
        f"{base(harness)}/channel-bindings/{bindings[0]['binding_id']}", headers=headers
    )
    assert revoke.status_code == 204
    assert client.get(f"{base(harness)}/channel-bindings").json()[0]["revoked_at"] is not None


def test_webhook_is_off_without_a_secret(harness: Any) -> None:
    app = FastAPI()
    app.include_router(build_channel_router(harness.channels, None))
    with TestClient(app) as http:
        assert http.post("/api/v1/channels/simulated/events", content=b"{}").status_code == 404
