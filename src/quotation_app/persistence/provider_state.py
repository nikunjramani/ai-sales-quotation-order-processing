"""Self-service connection writes and platform routes (phase 5).

- SqlConnectionLifecycle: Enable creates a connection in setting_up; every provisioning step
  is applied in one transaction (status, config, secret references, pending step, routes, a
  poll job and the audit event). A routing key taken by another connection rolls it all back.
- SqlRouteLookup: the platform webhook knows only a provider key and a routing key from the
  request; the connection_route_lookup policy reveals exactly that row (and nothing else).
- SqlRouteWriter: keys that route replies to a message we sent (one bot for everyone).
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Connection as DbConnection
from sqlalchemy import Engine, delete, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert

from quotation_app.domain.connections import ConnectionStatus
from quotation_app.domain.jobs import JobKind, JobStatus
from quotation_app.persistence.connections import record_event
from quotation_app.persistence.jobs import MAX_JOB_ATTEMPTS
from quotation_app.persistence.models import ConnectionRoute, ConnectionRow, Job
from quotation_app.persistence.tenancy import tenant_transaction
from quotation_app.ports.connections import ConnectionChange, RouteTaken


class SqlConnectionLifecycle:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(
        self,
        tenant_id: UUID,
        provider_key: str,
        display_name: str,
        purposes: Sequence[str],
        actor: str,
    ) -> UUID:
        connection_id = uuid4()
        with tenant_transaction(self._engine, tenant_id) as connection:
            connection.execute(
                insert(ConnectionRow).values(
                    id=connection_id,
                    tenant_id=tenant_id,
                    provider_key=provider_key,
                    display_name=display_name,
                    purposes=list(purposes),
                    config={},
                    status=ConnectionStatus.SETTING_UP.value,
                    created_by=actor,
                )
            )
            record_event(connection, tenant_id, connection_id, "created", actor)
        return connection_id

    def apply(
        self, tenant_id: UUID, connection_id: UUID, change: ConnectionChange, actor: str
    ) -> None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            provider_key = connection.execute(
                select(ConnectionRow.provider_key)
                .where(ConnectionRow.tenant_id == tenant_id, ConnectionRow.id == connection_id)
                .with_for_update()
            ).scalar_one()
            if change.remove_all_routes:
                connection.execute(
                    delete(ConnectionRoute).where(
                        ConnectionRoute.tenant_id == tenant_id,
                        ConnectionRoute.connection_id == connection_id,
                    )
                )
            elif change.remove_routes:
                connection.execute(
                    delete(ConnectionRoute).where(
                        ConnectionRoute.tenant_id == tenant_id,
                        ConnectionRoute.connection_id == connection_id,
                        ConnectionRoute.routing_key.in_(change.remove_routes),
                    )
                )
            for key, expires_at in change.add_routes.items():
                if not _add_route(
                    connection, tenant_id, connection_id, provider_key, key, expires_at
                ):
                    # Raising rolls the whole step back: nothing half-applied.
                    raise RouteTaken("This account is already connected to another business")
            connection.execute(
                update(ConnectionRow)
                .where(ConnectionRow.tenant_id == tenant_id, ConnectionRow.id == connection_id)
                .values(
                    status=change.status.value,
                    config=dict(change.config),
                    secret_refs=dict(change.secret_refs),
                    last_error=None if change.last_error is None else change.last_error[:300],
                    pending_action=(
                        None if change.pending_action is None else dict(change.pending_action)
                    ),
                    updated_at=text("now()"),
                )
            )
            if change.poll_at is not None:
                connection.execute(
                    insert(Job).values(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        kind=JobKind.POLL_CONNECTION.value,
                        payload={"connection_id": str(connection_id)},
                        status=JobStatus.PENDING.value,
                        max_attempts=MAX_JOB_ATTEMPTS,
                        run_at=change.poll_at,
                        correlation_id=uuid4(),
                    )
                )
            record_event(
                connection,
                tenant_id,
                connection_id,
                change.event_kind,
                actor,
                {"status": change.status.value, **change.detail},
            )

    def record_event(
        self,
        tenant_id: UUID,
        connection_id: UUID,
        kind: str,
        actor: str,
        detail: Mapping[str, object],
    ) -> None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            record_event(connection, tenant_id, connection_id, kind, actor, detail)


class SqlRouteLookup:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def resolve(self, provider_key: str, routing_key: str) -> tuple[UUID, UUID] | None:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    "SELECT set_config('app.route_provider', :p, true), "
                    "set_config('app.route_key', :k, true)"
                ),
                {"p": provider_key, "k": routing_key},
            )
            row = connection.execute(
                select(ConnectionRoute.tenant_id, ConnectionRoute.connection_id).where(
                    ConnectionRoute.provider_key == provider_key,
                    ConnectionRoute.routing_key == routing_key,
                    or_(
                        ConnectionRoute.expires_at.is_(None),
                        ConnectionRoute.expires_at > func.now(),
                    ),
                )
            ).one_or_none()
        return None if row is None else (row.tenant_id, row.connection_id)


class SqlRouteWriter:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add_routes(
        self,
        tenant_id: UUID,
        connection_id: UUID,
        provider_key: str,
        keys: Mapping[str, datetime | None],
    ) -> None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            for key, expires_at in keys.items():
                _add_route(connection, tenant_id, connection_id, provider_key, key, expires_at)


def _add_route(
    connection: DbConnection,
    tenant_id: UUID,
    connection_id: UUID,
    provider_key: str,
    key: str,
    expires_at: datetime | None,
) -> bool:
    """Insert one key for this connection; False if another business's connection has it.
    The same key on another connection of this business moves here (re-enabling a tool)."""
    connection.execute(
        delete(ConnectionRoute).where(
            ConnectionRoute.tenant_id == tenant_id,
            ConnectionRoute.provider_key == provider_key,
            ConnectionRoute.routing_key == key,
        )
    )
    inserted = connection.execute(
        insert(ConnectionRoute)
        .values(
            id=uuid4(),
            tenant_id=tenant_id,
            connection_id=connection_id,
            provider_key=provider_key,
            routing_key=key[:200],
            expires_at=expires_at,
        )
        .on_conflict_do_nothing(index_elements=["provider_key", "routing_key"])
        .returning(ConnectionRoute.id)
    ).scalar_one_or_none()
    return inserted is not None
