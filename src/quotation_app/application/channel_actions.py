"""Manager channel actions: enrollment (binding an account) and approval decisions.

Transport adapters verify the provider's signature first and pass a normalised ChannelEvent.
This service then checks that the account is enrolled, the action reference belongs to that
exact account and task, and hands the same DecisionCommand used by the portal to the
ApprovalService. A forwarded message used by another account fails; so does a revoked binding.
"""

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from quotation_app.application.api_keys import hash_secret
from quotation_app.application.approvals import ApprovalService, DecisionResult
from quotation_app.application.providers import ProviderRegistry
from quotation_app.domain.connections import Purpose
from quotation_app.domain.quotations import ApprovalAction, DecisionCommand
from quotation_app.domain.tenancy import Permission, TenantContext
from quotation_app.ports.channels import ChannelBinding, ChannelStore
from quotation_app.ports.connections import ConnectionStore

ENROLLMENT_LIFETIME = timedelta(minutes=10)


def utc_now() -> datetime:
    return datetime.now(UTC)


class ChannelActionRejected(Exception):
    """Unknown, expired, used, revoked or mismatched. One message for every reason."""


class ChannelEventKind(StrEnum):
    ENROLL = "enroll"
    DECISION = "decision"


@dataclass(frozen=True)
class ChannelEvent:
    """A provider event whose authenticity the transport adapter has already verified."""

    channel: str
    connection_id: str
    tenant_id: UUID
    event_id: str
    external_user_id: str
    kind: ChannelEventKind
    code: str | None = None  # enrollment code
    reference: str | None = None  # action reference token from the review message
    action: ApprovalAction | None = None
    reason: str | None = None


@dataclass(frozen=True)
class NewEnrollment:
    code: str
    expires_at: datetime
    provider_key: str
    connection_id: UUID | None  # set: the code works only on that connection


class ConnectionNotFound(Exception):
    """No such connection in this business (same message for another business's)."""


class ChannelActionService:
    def __init__(
        self,
        store: ChannelStore,
        approvals: ApprovalService,
        connections: ConnectionStore,
        registry: ProviderRegistry,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._approvals = approvals
        self._connections = connections
        self._registry = registry
        self._clock = clock

    def start_enrollment(
        self, context: TenantContext, provider_key: str, connection_id: UUID | None = None
    ) -> NewEnrollment:
        """A signed-in approver asks to link an account; the one-time code proves control.

        With connection_id the code works only on that connection (raises ConnectionNotFound,
        or ValueError if it is not an active manager-approval connection). Without it, any of
        the business's active connections of that provider (the older portal request).
        """
        context.require(Permission.APPROVE_QUOTATIONS)
        if connection_id is not None:
            connection = self._connections.get(context.tenant_id, connection_id)
            if connection is None:
                raise ConnectionNotFound("Not found")
            if not connection.active or not connection.serves(Purpose.MANAGER_APPROVALS):
                raise ValueError("This connection cannot be used for approvals")
            provider_key = connection.provider_key
        else:
            provider = self._registry.find(provider_key)
            linkable = [
                row
                for row in self._connections.list_for(context.tenant_id, Purpose.MANAGER_APPROVALS)
                if row.active and row.provider_key == provider_key
            ]
            if provider is None or Purpose.MANAGER_APPROVALS not in provider.purposes:
                raise ValueError(f"Unknown approval channel '{provider_key}'")
            if not linkable:
                raise ValueError(f"This business has no active '{provider_key}' connection")
        code = secrets.token_hex(5).upper()
        expires_at = self._clock() + ENROLLMENT_LIFETIME
        self._store.create_enrollment(
            context.tenant_id,
            context.subject,
            provider_key,
            hash_secret(code),
            expires_at,
            connection_id,
        )
        return NewEnrollment(code, expires_at, provider_key, connection_id)

    def bindings(self, context: TenantContext) -> list[ChannelBinding]:
        subject = None if Permission.MANAGE_TENANT in context.permissions else context.subject
        return self._store.bindings_for(context.tenant_id, subject)

    def revoke(self, context: TenantContext, binding_id: UUID) -> bool:
        subject = None if Permission.MANAGE_TENANT in context.permissions else context.subject
        return self._store.revoke(context.tenant_id, binding_id, subject)

    def handle(self, event: ChannelEvent) -> ChannelBinding | DecisionResult:
        if event.kind is ChannelEventKind.ENROLL:
            if not event.code:
                raise ChannelActionRejected("Action not accepted")
            binding = self._store.enroll(
                event.tenant_id,
                event.channel,
                event.connection_id,
                event.external_user_id,
                hash_secret(event.code.strip().upper()),
                self._clock(),
            )
            if binding is None:
                raise ChannelActionRejected("Action not accepted")
            return binding
        return self._decide(event)

    def _decide(self, event: ChannelEvent) -> DecisionResult:
        if not event.reference or event.action is None:
            raise ChannelActionRejected("Action not accepted")
        found = self._store.find_reference(event.tenant_id, hash_secret(event.reference))
        if found is None:
            raise ChannelActionRejected("Action not accepted")
        reference, binding = found
        now = self._clock()
        if (
            not binding.active
            or binding.channel != event.channel
            or binding.connection_id != event.connection_id
            or binding.external_user_id != event.external_user_id
            or (reference.consumed_at is None and reference.expires_at <= now)
        ):
            raise ChannelActionRejected("Action not accepted")
        # A consumed reference reaches the approval service only to return an exact replay
        # or a conflict: its task is no longer pending, so it can never create a new decision.
        command = DecisionCommand(
            command_id=uuid5(
                NAMESPACE_URL, f"channel:{event.channel}:{event.connection_id}:{event.event_id}"
            ),
            tenant_id=event.tenant_id,
            task_id=reference.task_id,
            content_sha256=reference.content_sha256,
            action=event.action,
            reason=event.reason,
            transport=event.channel,
            evidence_ref=f"{event.channel}:{event.connection_id}:{event.event_id}"[:300],
            received_at=now,
        )
        return self._approvals.decide(binding.subject, command, reference.reference_id)
