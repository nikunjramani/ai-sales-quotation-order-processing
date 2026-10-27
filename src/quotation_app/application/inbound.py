"""Provider callbacks on the generic hook route: verify, store once, route later (ADR 0018).

POST /api/v1/hooks/{connection_id}/{webhook_token} reaches InboundService.receive:
1. Find the connection by ID and compare the token's SHA-256 in constant time. Unknown,
   wrong token, not active, provider not installed or without webhooks: all the same
   HookNotFound, so a caller learns nothing about which check failed.
2. Refuse bodies larger than the provider allows.
3. The provider verifies the raw bytes (signature, timestamp) BEFORE anything is parsed.
4. The provider parses the body into normalised events. The tenant is always the
   connection's, never something named in the body.
5. Each event is stored once (dedupe on connection, provider event ID and type) together with
   a process_inbound job, in one transaction. The webhook answers at once; the job routes it.

Routing is by event type, never by provider: a manager action goes to the same
ChannelActionService (and ApprovalService) the portal's decisions use.
"""

import hashlib
import hmac
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from quotation_app.application.approvals import DecisionResult
from quotation_app.application.channel_actions import (
    ChannelActionRejected,
    ChannelActionService,
    ChannelEvent,
    ChannelEventKind,
)
from quotation_app.application.providers import ProviderRegistry
from quotation_app.domain.connections import Connection
from quotation_app.domain.intake import (
    InboundEvent,
    InboundEventType,
    ManagerAction,
    event_type,
    validate_event,
)
from quotation_app.domain.jobs import PermanentJobError
from quotation_app.domain.quotations import (
    ApprovalAction,
    DecisionConflict,
    StaleVersion,
    TaskNotFound,
)
from quotation_app.domain.tenancy import AuthorizationError
from quotation_app.ports.channels import ChannelBinding
from quotation_app.ports.connections import HookLookup
from quotation_app.ports.inbound import InboundStore
from quotation_app.ports.jobs import ClaimedJob
from quotation_app.ports.providers import InboundRequest, InvalidInbound
from quotation_app.ports.secrets import SecretStore

logger = logging.getLogger(__name__)
_DUMMY_HASH = "0" * 64


class HookNotFound(Exception):
    """Unknown connection, wrong token, not active or no webhook support (one message)."""


class EventTooLarge(Exception):
    pass


@dataclass(frozen=True)
class InboundReceipt:
    received: int
    duplicates: int


def token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InboundService:
    def __init__(
        self,
        hooks: HookLookup,
        registry: ProviderRegistry,
        secrets: SecretStore,
        store: InboundStore,
    ) -> None:
        self._hooks = hooks
        self._registry = registry
        self._secrets = secrets
        self._store = store

    def receive(
        self, connection_id: UUID, webhook_token: str, request: InboundRequest
    ) -> InboundReceipt:
        found = self._hooks.find_for_hook(connection_id)
        expected = found[1] if found is not None and found[1] else _DUMMY_HASH
        token_matches = hmac.compare_digest(token_sha256(webhook_token), expected)
        if found is None or not found[1] or not token_matches:
            raise HookNotFound("Not found")
        connection = found[0]
        provider = self._registry.find(connection.provider_key)
        if not connection.active or provider is None or not provider.capabilities.webhooks:
            raise HookNotFound("Not found")
        if len(request.body) > provider.capabilities.max_inbound_bytes:
            raise EventTooLarge("Event too large")
        provider.verify_inbound(connection, self._secrets, request)  # InboundRejected
        events = self._parse(connection, request)
        recorded = self._store.record(connection, events, request.received_at, queue_jobs=True)
        duplicates = sum(1 for item in recorded if not item.new)
        return InboundReceipt(received=len(recorded), duplicates=duplicates)

    def _parse(self, connection: Connection, request: InboundRequest) -> list[InboundEvent]:
        provider = self._registry.get(connection.provider_key)
        try:
            events = [
                validate_event(event) for event in provider.parse_inbound(connection, request)
            ]
        except ValueError:
            raise InvalidInbound("Invalid event") from None
        return events


class InboundRoute(Protocol):
    def __call__(self, connection: Connection, event: InboundEvent) -> str:
        """Act on one event and return the outcome to record. Raise to retry later."""
        ...


class ManagerActionRoute:
    """Enrollment codes and approval decisions from a linked manager account."""

    def __init__(self, actions: ChannelActionService) -> None:
        self._actions = actions

    def handle(
        self, connection: Connection, action: ManagerAction
    ) -> ChannelBinding | DecisionResult:
        """Route one action; raises the ChannelActionService's errors (the alias maps them)."""
        try:
            kind = ChannelEventKind(action.kind)
            decision = ApprovalAction(action.action) if action.action else None
        except ValueError:
            raise ChannelActionRejected("Action not accepted") from None
        return self._actions.handle(
            ChannelEvent(
                channel=connection.provider_key,
                connection_id=connection.legacy_key,
                tenant_id=connection.tenant_id,
                event_id=action.provider_event_id,
                external_user_id=action.external_user_id,
                kind=kind,
                code=action.code,
                reference=action.reference,
                action=decision,
                reason=action.reason,
            )
        )

    def __call__(self, connection: Connection, event: InboundEvent) -> str:
        assert isinstance(event, ManagerAction)
        try:
            result = self.handle(connection, event)
        except (ChannelActionRejected, AuthorizationError, TaskNotFound, ValueError):
            return "rejected"  # final: a retry cannot make it acceptable
        except (DecisionConflict, StaleVersion):
            return "conflict"
        if isinstance(result, DecisionResult):
            return "replayed" if result.replayed else "recorded"
        return "enrolled"


class ProcessInboundHandler:
    """Job handler for process_inbound: route one stored event, record its outcome once."""

    def __init__(
        self, store: InboundStore, routes: Mapping[InboundEventType, InboundRoute]
    ) -> None:
        self._store = store
        self._routes = dict(routes)

    def __call__(self, job: ClaimedJob) -> None:
        try:
            inbox_event_id = UUID(job.payload["inbox_event_id"])
        except (KeyError, ValueError):
            raise PermanentJobError("Job payload has no valid inbox_event_id") from None
        stored = self._store.load(job.tenant_id, inbox_event_id)
        if stored is None:
            raise PermanentJobError("Inbox event not found")
        if stored.processed_at is not None:
            return  # a retried job after the outcome was recorded
        route = self._routes.get(event_type(stored.event))
        if not stored.connection.active:
            outcome = "connection not active"
        elif route is None:
            outcome = "unsupported"
        else:
            outcome = route(stored.connection, stored.event)
        logger.info("Inbound event %s: %s", inbox_event_id, outcome)
        self._store.mark_processed(job.tenant_id, inbox_event_id, outcome[:300])


def routes_for(actions: ChannelActionService) -> Mapping[InboundEventType, InboundRoute]:
    """The routes available in phase 1; customer messages and receipts arrive in later items."""
    return {InboundEventType.MANAGER_ACTION: ManagerActionRoute(actions)}
