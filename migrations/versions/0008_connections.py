"""Connections: each business's configured tools (phase 1, ADR 0018).

- connections: one row per business tool (provider key, purposes, non-secret config, secret
  references only, provider-side account, webhook token hash, status). Forced tenant RLS.
  A narrow lookup policy lets the API read exactly the connection whose ID a webhook URL names
  (same pattern as api_key_lookup). At most one active catalogue source per business.
- connection_events: append-only audit of connection changes (never secrets).
- inbox_events gains event_type, connection_ref, processed_at and outcome; the dedupe key
  becomes (tenant, connection_ref, provider_event_id, event_type).
- channel_bindings and channel_enrollments gain connection_ref.
- The worker gains the grants to route manager actions from the process_inbound job.

Backfill: one `api` connection per API key (account_ref 'api-key:<id>', disabled if revoked),
one `simulated` connection per (tenant, connection_id) used by bindings, a disabled safety-net
connection for any other inbox source, then every inbox event and binding is linked. The old
`channel` / `connection_id` columns stay filled (deprecated) for display compatibility.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_connections"
down_revision = "0007_acceptance"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_PURPOSES = "'customer_messages', 'manager_approvals', 'catalogue', 'payments', 'orders'"
_EVENT_TYPES = "'customer_message', 'manager_action', 'delivery_status', 'consent_change'"
_CONNECTION_EVENT_KINDS = (
    "'created', 'migrated', 'status_changed', 'tested', 'provisioned', 'deprovisioned'"
)
_NOW = sa.text("now()")


def _isolate(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )


def _connection_ref(table: str) -> None:
    """Nullable at first; inbox events and bindings become NOT NULL after the backfill."""
    op.add_column(table, sa.Column("connection_ref", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        f"fk_{table}_connection",
        table,
        "connections",
        ["tenant_id", "connection_ref"],
        ["tenant_id", "id"],
    )


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider_key", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("purposes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "secret_refs", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("account_ref", sa.String(200), nullable=True),
        sa.Column("webhook_token_sha256", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_connections"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_connections_tenant_id_tenants"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_connections_tenant_id_id"),
        sa.UniqueConstraint(
            "tenant_id", "provider_key", "account_ref", name="uq_connections_account"
        ),
        sa.CheckConstraint(
            "provider_key ~ '^[a-z][a-z0-9_]{1,31}$'", name="ck_connections_provider_key"
        ),
        sa.CheckConstraint(
            f"cardinality(purposes) >= 1 AND purposes <@ ARRAY[{_PURPOSES}]::text[]",
            name="ck_connections_purposes",
        ),
        sa.CheckConstraint(
            "status IN ('setting_up', 'active', 'error', 'disabled')",
            name="ck_connections_status",
        ),
    )
    op.create_index("ix_connections_tenant_status", "connections", ["tenant_id", "status"])
    op.create_index(
        "uq_connections_one_catalogue",
        "connections",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND purposes @> ARRAY['catalogue']::text[]"),
    )
    op.create_table(
        "connection_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("detail", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_connection_events"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_id"],
            ["connections.tenant_id", "connections.id"],
            name="fk_connection_events_connection",
        ),
        sa.CheckConstraint(
            f"kind IN ({_CONNECTION_EVENT_KINDS})", name="ck_connection_events_kind"
        ),
    )
    op.create_index(
        "ix_connection_events_connection",
        "connection_events",
        ["tenant_id", "connection_id", "created_at"],
    )
    for table in ("connections", "connection_events"):
        _isolate(table)
    op.execute(
        "CREATE TRIGGER connection_events_immutable BEFORE UPDATE OR DELETE ON connection_events "
        "FOR EACH ROW EXECUTE FUNCTION reject_change()"
    )
    # The generic webhook route knows only the connection ID from its URL. This policy reveals
    # only the row whose ID the caller set; the webhook token hash must still match.
    op.execute(
        "CREATE POLICY connection_hook_lookup ON connections FOR SELECT TO quotation_app "
        "USING (id = NULLIF(current_setting('app.connection_id', true), '')::uuid)"
    )

    op.add_column(
        "inbox_events",
        sa.Column(
            "event_type",
            sa.String(32),
            server_default=sa.text("'customer_message'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_inbox_events_event_type", "inbox_events", f"event_type IN ({_EVENT_TYPES})"
    )
    op.add_column(
        "inbox_events", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("inbox_events", sa.Column("outcome", sa.String(300), nullable=True))
    for table in ("inbox_events", "channel_bindings", "channel_enrollments"):
        _connection_ref(table)

    _backfill()

    for table in ("inbox_events", "channel_bindings"):
        op.alter_column(table, "connection_ref", nullable=False)
    op.drop_constraint("uq_inbox_events_provider_event", "inbox_events", type_="unique")
    op.create_unique_constraint(
        "uq_inbox_events_provider_event",
        "inbox_events",
        ["tenant_id", "connection_ref", "provider_event_id", "event_type"],
    )
    op.drop_index("uq_channel_bindings_active_account", table_name="channel_bindings")
    op.create_index(
        "uq_channel_bindings_active_account",
        "channel_bindings",
        ["tenant_id", "connection_ref", "external_user_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.execute("GRANT SELECT ON connections, connection_events TO quotation_app")
    op.execute("GRANT UPDATE (processed_at, outcome) ON inbox_events TO quotation_app")
    op.execute("GRANT SELECT ON connections, connection_events TO quotation_worker")
    op.execute("GRANT INSERT, UPDATE (processed_at, outcome) ON inbox_events TO quotation_worker")
    op.execute("GRANT INSERT ON enquiries TO quotation_worker")
    # Manager actions arriving on the generic hook are routed in the process_inbound job.
    op.execute("GRANT INSERT ON approval_decisions, channel_bindings TO quotation_worker")
    op.execute("GRANT UPDATE (status, decided_at) ON approval_tasks TO quotation_worker")
    op.execute("GRANT SELECT, UPDATE (consumed_at) ON channel_enrollments TO quotation_worker")
    op.execute("GRANT UPDATE (consumed_at) ON approval_action_refs TO quotation_worker")


def _backfill() -> None:
    # FORCE RLS hides rows from the owner too; lift it inside this transaction only.
    tables = ("connections", "connection_events", "api_keys", "inbox_events", "channel_bindings")
    for table in tables:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(
        "INSERT INTO connections (id, tenant_id, provider_key, display_name, purposes, "
        "account_ref, status, created_by) "
        "SELECT gen_random_uuid(), tenant_id, 'api', name, ARRAY['customer_messages'], "
        "'api-key:' || id, CASE WHEN revoked_at IS NULL THEN 'active' ELSE 'disabled' END, "
        "'migration:0008' FROM api_keys"
    )
    op.execute(
        "INSERT INTO connections (id, tenant_id, provider_key, display_name, purposes, "
        "account_ref, status, created_by) "
        "SELECT gen_random_uuid(), b.tenant_id, b.channel, left(b.channel || ' ' || "
        "b.connection_id, 100), ARRAY['manager_approvals'], b.connection_id, 'active', "
        "'migration:0008' FROM (SELECT DISTINCT tenant_id, channel, connection_id "
        "FROM channel_bindings) b ON CONFLICT (tenant_id, provider_key, account_ref) DO NOTHING"
    )
    op.execute(
        "INSERT INTO connections (id, tenant_id, provider_key, display_name, purposes, "
        "account_ref, status, created_by) "
        "SELECT gen_random_uuid(), e.tenant_id, e.channel, left(e.channel || ' ' || "
        "e.connection_id, 100), ARRAY['customer_messages'], e.connection_id, 'disabled', "
        "'migration:0008' FROM (SELECT DISTINCT tenant_id, channel, connection_id "
        "FROM inbox_events) e ON CONFLICT (tenant_id, provider_key, account_ref) DO NOTHING"
    )
    op.execute(
        "INSERT INTO connection_events (id, tenant_id, connection_id, kind, actor) "
        "SELECT gen_random_uuid(), tenant_id, id, 'migrated', 'migration:0008' FROM connections"
    )
    for table in ("inbox_events", "channel_bindings"):
        op.execute(
            f"UPDATE {table} t SET connection_ref = c.id FROM connections c "
            "WHERE c.tenant_id = t.tenant_id AND c.provider_key = t.channel "
            "AND c.account_ref = t.connection_id"
        )
    # The address to send the quotation back to, fixed at intake from now on. The API is the
    # only pull provider before this migration (frozen here; code decides by capability).
    op.execute(
        "UPDATE inbox_events SET envelope = envelope || jsonb_build_object('reply_to', "
        "CASE WHEN channel = 'api' THEN connection_id "
        "ELSE envelope->>'sender_external_id' END)"
    )
    for table in tables:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (consumed_at) ON approval_action_refs FROM quotation_worker")
    op.execute("REVOKE SELECT, UPDATE (consumed_at) ON channel_enrollments FROM quotation_worker")
    op.execute("REVOKE UPDATE (status, decided_at) ON approval_tasks FROM quotation_worker")
    op.execute("REVOKE INSERT ON approval_decisions, channel_bindings FROM quotation_worker")
    op.execute("REVOKE INSERT ON enquiries FROM quotation_worker")
    op.execute(
        "REVOKE INSERT, UPDATE (processed_at, outcome) ON inbox_events FROM quotation_worker"
    )
    op.execute("REVOKE UPDATE (processed_at, outcome) ON inbox_events FROM quotation_app")

    for table in ("inbox_events", "jobs"):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    # Events other than customer messages have no enquiry and cannot exist before phase 1.
    op.execute("DELETE FROM inbox_events WHERE event_type <> 'customer_message'")
    op.execute("DELETE FROM jobs WHERE kind IN ('process_inbound', 'provision_connection')")
    op.execute("UPDATE inbox_events SET envelope = envelope - 'reply_to'")
    for table in ("inbox_events", "jobs"):
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.drop_index("uq_channel_bindings_active_account", table_name="channel_bindings")
    op.create_index(
        "uq_channel_bindings_active_account",
        "channel_bindings",
        ["tenant_id", "channel", "connection_id", "external_user_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_constraint("uq_inbox_events_provider_event", "inbox_events", type_="unique")
    op.create_unique_constraint(
        "uq_inbox_events_provider_event",
        "inbox_events",
        ["tenant_id", "channel", "connection_id", "provider_event_id"],
    )
    for table in ("channel_enrollments", "channel_bindings", "inbox_events"):
        op.drop_constraint(f"fk_{table}_connection", table, type_="foreignkey")
        op.drop_column(table, "connection_ref")
    op.drop_constraint("ck_inbox_events_event_type", "inbox_events", type_="check")
    for column in ("outcome", "processed_at", "event_type"):
        op.drop_column("inbox_events", column)
    op.drop_table("connection_events")
    op.drop_table("connections")
