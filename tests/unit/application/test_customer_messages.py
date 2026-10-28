"""Which customer messages are queued, where to, and the consent check at send time."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from quotation_app.application.customer_messages import (
    OPTED_OUT_REASON,
    CustomerConsentHook,
    CustomerMessenger,
)
from quotation_app.application.messaging import OutboundService
from quotation_app.application.providers import ProviderRegistry
from quotation_app.domain.connections import (
    Capabilities,
    Connection,
    ConnectionStatus,
    DeliveryMode,
    Purpose,
)
from quotation_app.domain.contacts import ConsentStatus
from quotation_app.domain.messages import MessageStatus, OutboundMessage, TemplateKey
from quotation_app.ports.conversations import CustomerTarget
from quotation_app.ports.messages import NewMessage

TENANT = uuid4()
NOW = datetime(2026, 10, 28, tzinfo=UTC)


@dataclass
class Tool:
    key: str
    capabilities: Capabilities


class Registry:
    def __init__(self, *tools: Tool) -> None:
        self.tools = {tool.key: tool for tool in tools}

    def find(self, key: str) -> Tool | None:
        return self.tools.get(key)


def connection(provider: str) -> Connection:
    return Connection(
        uuid4(), TENANT, provider, provider, frozenset({Purpose.CUSTOMER_MESSAGES}), {}, {},
        None, ConnectionStatus.ACTIVE, None, "test", NOW, NOW,
    )  # fmt: skip


@dataclass
class World:
    connections: dict[UUID, Connection] = field(default_factory=dict)
    targets: dict[UUID, CustomerTarget] = field(default_factory=dict)
    consents: dict[tuple[UUID, str], ConsentStatus] = field(default_factory=dict)
    queued: list[NewMessage] = field(default_factory=list)

    # ConnectionStore (only get is used)
    def get(self, tenant_id: UUID, connection_id: UUID) -> Connection | None:
        return self.connections.get(connection_id)

    # CustomerTargets
    def for_enquiry(self, tenant_id: UUID, enquiry_id: UUID) -> CustomerTarget | None:
        return self.targets.get(enquiry_id)

    def consent(self, tenant_id: UUID, connection_id: UUID, external_id: str) -> ConsentStatus:
        return self.consents.get((connection_id, external_id), ConsentStatus.IMPLIED)

    # MessageOutbox (only enqueue is used)
    def enqueue(self, message: NewMessage) -> UUID:
        self.queued.append(message)
        return uuid4()

    def add(self, provider: str, acknowledge: bool = True) -> UUID:
        conn = connection(provider)
        self.connections[conn.connection_id] = conn
        enquiry_id = uuid4()
        self.targets[enquiry_id] = CustomerTarget(
            uuid4(), conn.connection_id, uuid4(), f"visitor-{provider}", ConsentStatus.IMPLIED,
            acknowledge,
        )  # fmt: skip
        return enquiry_id


@pytest.fixture
def world() -> World:
    return World()


@pytest.fixture
def messenger(world: World) -> CustomerMessenger:
    registry = Registry(
        Tool("chat", Capabilities(delivery_mode=DeliveryMode.PUSH)),
        Tool("api", Capabilities(delivery_mode=DeliveryMode.PULL)),
    )
    return CustomerMessenger(
        world,
        cast(Any, world),
        cast(ProviderRegistry, registry),
        OutboundService(cast(Any, world)),
    )


def test_a_push_conversation_gets_the_message_in_its_thread(
    world: World, messenger: CustomerMessenger
) -> None:
    enquiry_id = world.add("chat")
    messenger.send(TENANT, enquiry_id, TemplateKey.ENQUIRY_RECEIVED, {}, "ack:1", uuid4())
    [message] = world.queued
    target = world.targets[enquiry_id]
    assert message.recipient == "visitor-chat"
    assert message.links.conversation_id == target.conversation_id
    assert message.links.enquiry_id == enquiry_id
    assert message.body_text == "Thanks, we are preparing your quotation."


def test_pull_tools_and_enquiries_without_a_conversation_get_nothing(
    world: World, messenger: CustomerMessenger
) -> None:
    api_enquiry = world.add("api")
    for enquiry_id in (api_enquiry, uuid4()):
        messenger.send(TENANT, enquiry_id, TemplateKey.ENQUIRY_RECEIVED, {}, "k", uuid4())
    assert world.queued == []


def test_the_acknowledgement_follows_the_business_setting(
    world: World, messenger: CustomerMessenger
) -> None:
    messenger.acknowledge(TENANT, world.add("chat", acknowledge=False), uuid4())
    assert world.queued == []
    wanted = world.add("chat", acknowledge=True)
    messenger.acknowledge(TENANT, wanted, uuid4())
    assert [m.idempotency_key for m in world.queued] == [f"ack:{wanted}"]


def outbound(template: TemplateKey, connection_id: UUID, recipient: str) -> OutboundMessage:
    return OutboundMessage(
        uuid4(), TENANT, connection_id, "chat", Purpose.CUSTOMER_MESSAGES, template, {},
        recipient, "key", "text", {}, MessageStatus.PENDING, None, None, None, None, None,
        None, None, uuid4(), None, None, NOW, NOW,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("template", "cancelled"),
    [(TemplateKey.QUOTATION_READY, True), (TemplateKey.OPTED_OUT, False)],
)
def test_opted_out_customers_only_get_the_confirmation(
    world: World, template: TemplateKey, cancelled: bool
) -> None:
    connection_id = uuid4()
    world.consents[(connection_id, "visitor")] = ConsentStatus.OPTED_OUT
    prepared = CustomerConsentHook(world).before_send(outbound(template, connection_id, "visitor"))
    assert prepared.cancel_reason == (OPTED_OUT_REASON if cancelled else None)


def test_the_consent_hook_hands_over_to_the_template_hook(world: World) -> None:
    class Inner:
        def before_send(self, message: OutboundMessage) -> Any:
            from quotation_app.ports.messages import SendPreparation

            return SendPreparation(actions=("accept", "decline"))

        def after_send(self, *args: Mapping[str, object]) -> None:
            return None

    hook = CustomerConsentHook(world, cast(Any, Inner()))
    prepared = hook.before_send(outbound(TemplateKey.QUOTATION_READY, uuid4(), "visitor"))
    assert prepared.actions == ("accept", "decline")


def test_every_recorded_answer_has_a_customer_message() -> None:
    from quotation_app.application.acceptance import CUSTOMER_TEMPLATE_FOR
    from quotation_app.domain.acceptance import ResponseOutcome

    assert set(CUSTOMER_TEMPLATE_FOR) == set(ResponseOutcome)
