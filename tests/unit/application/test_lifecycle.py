"""One-click Enable, setup steps, setup events, polling, Test and Disable (phase 5)."""

from datetime import datetime, timedelta
from uuid import UUID

import pytest

from quotation_app.adapters.secrets.memory import InMemorySecretStore
from quotation_app.application.channel_actions import ConnectionNotFound
from quotation_app.application.lifecycle import (
    ActionNotFound,
    ConnectionLifecycle,
    CostsNotAccepted,
)
from quotation_app.application.providers import ProviderRegistry
from quotation_app.domain.connections import ConnectionStatus
from quotation_app.domain.intake import ConnectionUpdate
from quotation_app.domain.jobs import JobKind
from quotation_app.domain.tenancy import PermissionDenied, Role, TenantContext
from quotation_app.ports.connections import RouteTaken
from quotation_app.ports.jobs import ClaimedJob
from quotation_app.ports.providers import CostNote, PendingActionKind
from tests.unit.conftest import MemoryConnections
from tests.unit.one_click import TOOL, MemoryLifecycle, OneClickTool


class Setup:
    def __init__(self, now: datetime, *tenants: UUID, cost: CostNote | None = None) -> None:
        self.tool = OneClickTool(now) if cost is None else OneClickTool(now, cost)
        self.connections = MemoryConnections(now, *tenants)
        self.store = MemoryLifecycle(self.connections, now)
        self.secrets = InMemorySecretStore()
        self.service = ConnectionLifecycle(
            self.connections,
            self.store,
            ProviderRegistry([self.tool]),
            self.secrets,
            clock=lambda: now,
        )


def admin(tenant_id: UUID) -> TenantContext:
    return TenantContext(tenant_id, "user:admin", frozenset({Role.ADMINISTRATOR}))


@pytest.fixture
def setup(now: datetime, industrial_tenant: UUID, office_tenant: UUID) -> Setup:
    return Setup(now, industrial_tenant, office_tenant)


def test_only_administrators_enable_tools(setup: Setup, industrial_tenant: UUID) -> None:
    operator = TenantContext(industrial_tenant, "user:op", frozenset({Role.SALES_OPERATOR}))
    with pytest.raises(PermissionDenied):
        setup.service.enable(operator, TOOL, accept_costs=False)
    with pytest.raises(PermissionDenied):
        setup.service.available(operator)
    assert [tool.key for tool in setup.service.available(admin(industrial_tenant))] == [TOOL]


def test_a_tool_with_costs_needs_the_tick(now: datetime, industrial_tenant: UUID) -> None:
    paid = Setup(now, industrial_tenant, cost=CostNote(free=False, text="About $1 a month"))
    with pytest.raises(CostsNotAccepted):
        paid.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    outcome = paid.service.enable(admin(industrial_tenant), TOOL, accept_costs=True)
    assert outcome.connection.status is ConnectionStatus.SETTING_UP


def test_enable_gives_one_step_and_the_code_only_once(
    setup: Setup, industrial_tenant: UUID
) -> None:
    outcome = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)

    assert outcome.connection.status is ConnectionStatus.SETTING_UP
    assert outcome.pending is not None
    assert outcome.pending.kind is PendingActionKind.SHOW_STEPS
    assert outcome.pending.once == {"code": "CODE1"}
    stored = outcome.connection.pending_action
    assert stored is not None and stored["action_id"] == "link"
    assert "CODE1" not in str(stored)  # one-time values are never stored
    assert setup.store.keys_of(outcome.connection.connection_id) == {"link:CODE1"}


def test_enable_again_replaces_the_code(setup: Setup, industrial_tenant: UUID) -> None:
    first = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    second = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)

    assert second.connection.connection_id == first.connection.connection_id
    assert second.pending is not None and second.pending.once == {"code": "CODE2"}
    assert setup.store.keys_of(first.connection.connection_id) == {"link:CODE2"}


def test_a_setup_event_finishes_the_connection(setup: Setup, industrial_tenant: UUID) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)

    outcome = setup.service.on_update(
        started.connection, ConnectionUpdate("u-1", "link", {"owner": "acme"})
    )

    row = setup.connections.get(industrial_tenant, started.connection.connection_id)
    assert outcome == "active"
    assert row is not None and row.active and row.pending_action is None
    assert row.config["public_detail"] == "Customers can write to @acme"
    assert setup.store.keys_of(row.connection_id) == {"owner:acme"}
    # The secret is in the secret store; the connection keeps only its reference.
    assert setup.secrets.get(industrial_tenant, row.secret_refs["token"]) == "token-of-acme"
    assert "token-of-acme" not in str(row)


def test_enable_on_an_active_tool_returns_it_without_provisioning(
    setup: Setup, industrial_tenant: UUID
) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    setup.service.on_update(started.connection, ConnectionUpdate("u-1", "link", {"owner": "a"}))

    again = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)

    assert again.connection.active and again.pending is None
    assert setup.tool.codes == 1


def test_an_account_of_another_business_is_refused_and_nothing_changes(
    setup: Setup, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    first = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    setup.service.on_update(first.connection, ConnectionUpdate("u-1", "link", {"owner": "same"}))
    other = setup.service.enable(admin(office_tenant), TOOL, accept_costs=False)

    with pytest.raises(RouteTaken):
        setup.service.on_update(
            other.connection, ConnectionUpdate("u-2", "link", {"owner": "same"})
        )

    row = setup.connections.get(office_tenant, other.connection.connection_id)
    assert row is not None and row.status is ConnectionStatus.SETTING_UP
    assert row.secret_refs == {}
    # The refused step's secret was removed again: only the first business's token is left.
    assert len(setup.secrets._values) == 1


def test_a_failed_step_shows_the_error(setup: Setup, industrial_tenant: UUID) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    assert setup.service.on_update(started.connection, ConnectionUpdate("u", "off", {})) == "error"
    row = setup.connections.get(industrial_tenant, started.connection.connection_id)
    assert row is not None and row.last_error == "The tool was switched off"


def test_resume_needs_the_current_step_that_returns_data(
    setup: Setup, industrial_tenant: UUID
) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    connection_id = started.connection.connection_id
    with pytest.raises(ActionNotFound):  # a show_steps step returns nothing to us
        setup.service.resume(admin(industrial_tenant), connection_id, "link", {"owner": "x"})
    with pytest.raises(ActionNotFound):
        setup.service.resume(admin(industrial_tenant), connection_id, "other", {})


def test_polling_asks_the_tool_again_later(
    setup: Setup, industrial_tenant: UUID, now: datetime
) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    job = ClaimedJob(
        started.connection.connection_id,
        industrial_tenant,
        JobKind.POLL_CONNECTION,
        {"connection_id": str(started.connection.connection_id)},
        1,
        5,
        started.connection.connection_id,
        started.connection.connection_id,
    )

    setup.service.poll(job)

    assert setup.store.polls == [(started.connection.connection_id, now + timedelta(minutes=5))]


def test_disable_removes_routes_and_says_what_is_left(
    setup: Setup, industrial_tenant: UUID
) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    connection_id = started.connection.connection_id

    steps = setup.service.disable(admin(industrial_tenant), connection_id)

    row = setup.connections.get(industrial_tenant, connection_id)
    assert steps == ("Remove our bot in the tool's settings",)
    assert row is not None and row.status is ConnectionStatus.DISABLED
    assert setup.store.keys_of(connection_id) == set()
    assert setup.service.on_update(row, ConnectionUpdate("u", "link", {"owner": "a"})) == "ignored"


def test_test_reports_the_tool_answer(setup: Setup, industrial_tenant: UUID) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    result = setup.service.test(admin(industrial_tenant), started.connection.connection_id)
    assert (result.ok, result.detail) == (False, "not linked")
    assert setup.store.events[-1][1] == "tested"


def test_another_business_cannot_touch_the_connection(
    setup: Setup, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    started = setup.service.enable(admin(industrial_tenant), TOOL, accept_costs=False)
    with pytest.raises(ConnectionNotFound):
        setup.service.disable(admin(office_tenant), started.connection.connection_id)
