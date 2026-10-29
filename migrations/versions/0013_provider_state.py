"""Provider framework state: platform routes, approval by message, media links (phase 5).

- connection_routes: a routing key (Telegram business connection, a link code, a reply to one
  of our messages...) that names one connection, for providers with one webhook for the whole
  platform (one bot, one app). The key is unique across all businesses; the lookup policy
  reveals only the row whose exact key was presented, like api_key_lookup. Keys may expire.
- approval_reply_prompts: a question we asked a linked manager about one approval request:
  "reply with the reason" after a Reject/Change button (kind reason) or "You want to approve
  Q-... version N? Yes/No" after the AI read a written reply (kind confirm, user answer
  P5-13). A reply to the prompt's message, or its Yes/No buttons, completes it once.
- manager_reply_classifications: append-only audit of every written manager reply: its text
  and SHA-256, what the reader (AI or rules) understood, which safety guard fired, outcome.
- media_links: short-lived public links to one approved PDF, for providers that fetch
  attachments by URL (C6). Only the token's SHA-256 is stored.
- outbound_messages gains action_ref_id (the approval request a message belongs to, so a reply
  to it finds the request) and resent_from_id (a staff Resend of a failed message).
- connections gains pending_action: the step the business still has to do (shown in the
  portal; one-time values such as a link code are never stored).
- inbox_events accepts manager_reply, customer_action and connection_update events.
- Grants: both roles manage routes and prompts; the worker updates connections (a setup event
  finishes the linking) and links messages to action references; the API may insert outbox
  messages (Resend) and look up an approval request by its link token (signed link page).

Downgrade deletes the new event types, prompts, classifications, routes and media links.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_provider_state"
down_revision = "0012_conversations"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_NOW = sa.text("now()")
_NEW_TABLES = (
    "connection_routes",
    "approval_reply_prompts",
    "manager_reply_classifications",
    "media_links",
)
_EVENT_TYPES_OLD = "'customer_message', 'manager_action', 'delivery_status', 'consent_change'"
_EVENT_TYPES_NEW = _EVENT_TYPES_OLD + ", 'manager_reply', 'customer_action', 'connection_update'"
_CONNECTION_EVENT_KINDS_OLD = (
    "'created', 'migrated', 'status_changed', 'tested', 'provisioned', 'deprovisioned', "
    "'settings_changed'"
)
_CONNECTION_EVENT_KINDS_NEW = _CONNECTION_EVENT_KINDS_OLD + ", 'resumed'"
_APP_CONNECTION_INSERT_OLD = (
    "id, tenant_id, provider_key, display_name, purposes, config, account_ref, status, created_by"
)
_APP_CONNECTION_INSERT_NEW = _APP_CONNECTION_INSERT_OLD + ", secret_refs, pending_action"
_CONNECTION_STATE = "status, config, secret_refs, last_error, pending_action, updated_at"


def _created() -> sa.Column[Any]:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False)


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], name=f"fk_{table}_tenant_id_tenants"
    )


def upgrade() -> None:
    op.create_table(
        "connection_routes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("provider_key", sa.String(32), nullable=False),
        sa.Column("routing_key", sa.String(200), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_connection_routes"),
        _tenant_fk("connection_routes"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_id"],
            ["connections.tenant_id", "connections.id"],
            name="fk_connection_routes_connection",
        ),
        sa.UniqueConstraint("provider_key", "routing_key", name="uq_connection_routes_key"),
    )
    op.create_index(
        "ix_connection_routes_connection", "connection_routes", ["tenant_id", "connection_id"]
    )

    op.add_column("outbound_messages", sa.Column("action_ref_id", sa.Uuid(), nullable=True))
    op.add_column("outbound_messages", sa.Column("resent_from_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_outbound_messages_action_ref",
        "outbound_messages",
        "approval_action_refs",
        ["action_ref_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_outbound_messages_resent_from",
        "outbound_messages",
        "outbound_messages",
        ["tenant_id", "resent_from_id"],
        ["tenant_id", "id"],
    )
    op.create_index(
        "ix_outbound_messages_action_ref", "outbound_messages", ["tenant_id", "action_ref_id"]
    )

    op.create_table(
        "approval_reply_prompts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("token_sha256", sa.String(64), nullable=True),
        sa.Column("outbound_message_id", sa.Uuid(), nullable=True),
        sa.Column("inbox_event_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=True),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_approval_reply_prompts"),
        _tenant_fk("approval_reply_prompts"),
        sa.ForeignKeyConstraint(
            ["reference_id"], ["approval_action_refs.id"], name="fk_approval_reply_prompts_ref"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "outbound_message_id"],
            ["outbound_messages.tenant_id", "outbound_messages.id"],
            name="fk_approval_reply_prompts_message",
        ),
        sa.UniqueConstraint("token_sha256", name="uq_approval_reply_prompts_token"),
        sa.UniqueConstraint("outbound_message_id", name="uq_approval_reply_prompts_message"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "inbox_event_id"],
            ["inbox_events.tenant_id", "inbox_events.id"],
            name="fk_approval_reply_prompts_event",
        ),
        sa.UniqueConstraint("inbox_event_id", name="uq_approval_reply_prompts_event"),
        sa.CheckConstraint("kind IN ('reason', 'confirm')", name="ck_approval_reply_prompts_kind"),
        sa.CheckConstraint(
            "action IN ('approve', 'reject', 'request_revision')",
            name="ck_approval_reply_prompts_action",
        ),
        sa.CheckConstraint(
            "(closed_at IS NULL) = (outcome IS NULL)", name="ck_approval_reply_prompts_closed"
        ),
        sa.CheckConstraint(
            "reason IS NULL OR length(reason) <= 1000", name="ck_approval_reply_prompts_reason"
        ),
    )
    # At most one open prompt per approval request: a new one closes the earlier one first.
    op.create_index(
        "uq_approval_reply_prompts_open",
        "approval_reply_prompts",
        ["tenant_id", "reference_id"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
    )

    op.create_table(
        "manager_reply_classifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("inbox_event_id", sa.Uuid(), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("intent", sa.String(16), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("guard", sa.String(64), nullable=True),
        sa.Column("outcome", sa.String(64), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_manager_reply_classifications"),
        _tenant_fk("manager_reply_classifications"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "inbox_event_id"],
            ["inbox_events.tenant_id", "inbox_events.id"],
            name="fk_manager_reply_classifications_event",
        ),
        sa.ForeignKeyConstraint(
            ["reference_id"],
            ["approval_action_refs.id"],
            name="fk_manager_reply_classifications_ref",
        ),
        sa.UniqueConstraint("inbox_event_id", name="uq_manager_reply_classifications_event"),
        sa.CheckConstraint(
            "intent IN ('approve', 'reject', 'revise', 'unclear')",
            name="ck_manager_reply_classifications_intent",
        ),
        sa.CheckConstraint("length(text) <= 4000", name="ck_manager_reply_classifications_text"),
    )

    op.create_table(
        "media_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("token_sha256", sa.String(64), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("outbound_message_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_media_links"),
        _tenant_fk("media_links"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            ["quotation_documents.tenant_id", "quotation_documents.id"],
            name="fk_media_links_document",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "outbound_message_id"],
            ["outbound_messages.tenant_id", "outbound_messages.id"],
            name="fk_media_links_message",
        ),
        sa.UniqueConstraint("token_sha256", name="uq_media_links_token"),
    )

    op.add_column("connections", sa.Column("pending_action", postgresql.JSONB(), nullable=True))
    op.drop_constraint("ck_inbox_events_event_type", "inbox_events", type_="check")
    op.create_check_constraint(
        "ck_inbox_events_event_type", "inbox_events", f"event_type IN ({_EVENT_TYPES_NEW})"
    )
    op.drop_constraint("ck_connection_events_kind", "connection_events", type_="check")
    op.create_check_constraint(
        "ck_connection_events_kind",
        "connection_events",
        f"kind IN ({_CONNECTION_EVENT_KINDS_NEW})",
    )

    for table in _NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
        )
    # Before the tenant is known, each reveals only the one row whose key was presented.
    op.execute(
        "CREATE POLICY connection_route_lookup ON connection_routes FOR SELECT "
        "TO quotation_app, quotation_worker USING ("
        "provider_key = NULLIF(current_setting('app.route_provider', true), '') "
        "AND routing_key = NULLIF(current_setting('app.route_key', true), ''))"
    )
    op.execute(
        "CREATE POLICY media_link_lookup ON media_links FOR SELECT TO quotation_app "
        "USING (token_sha256 = NULLIF(current_setting('app.media_token_sha256', true), ''))"
    )
    op.execute(
        "CREATE POLICY approval_link_lookup ON approval_action_refs FOR SELECT TO quotation_app "
        "USING (token_sha256 = NULLIF(current_setting('app.approval_token_sha256', true), ''))"
    )
    op.execute(
        "CREATE TRIGGER manager_reply_classifications_immutable BEFORE UPDATE OR DELETE "
        "ON manager_reply_classifications FOR EACH ROW EXECUTE FUNCTION reject_change()"
    )

    for role in ("quotation_app", "quotation_worker"):
        op.execute(f"GRANT SELECT, INSERT, DELETE ON connection_routes TO {role}")
        op.execute(
            "GRANT SELECT, INSERT, UPDATE (token_sha256, outbound_message_id, closed_at, outcome) "
            f"ON approval_reply_prompts TO {role}"
        )
    op.execute("GRANT SELECT, INSERT ON manager_reply_classifications TO quotation_worker")
    op.execute("GRANT SELECT ON manager_reply_classifications TO quotation_app")
    op.execute("GRANT SELECT, INSERT ON media_links TO quotation_worker")
    op.execute("GRANT SELECT ON media_links TO quotation_app")
    op.execute("GRANT INSERT ON outbound_messages TO quotation_app")
    # Resend points a failed quotation delivery at its new message.
    op.execute("GRANT UPDATE (outbound_message_id) ON quotation_deliveries TO quotation_app")
    op.execute("GRANT UPDATE (action_ref_id) ON outbound_messages TO quotation_worker")
    op.execute(
        f"GRANT INSERT ({_APP_CONNECTION_INSERT_NEW}), UPDATE ({_CONNECTION_STATE}) "
        "ON connections TO quotation_app"
    )
    op.execute(f"GRANT UPDATE ({_CONNECTION_STATE}) ON connections TO quotation_worker")
    op.execute("GRANT INSERT ON connection_events TO quotation_worker")
    # Customer Accept/Decline pressed in a webhook tool is answered in the worker.
    op.execute(
        "GRANT UPDATE (consumed_at, response_id) ON customer_action_refs TO quotation_worker"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE UPDATE (consumed_at, response_id) ON customer_action_refs FROM quotation_worker"
    )
    op.execute("REVOKE INSERT ON connection_events FROM quotation_worker")
    op.execute("REVOKE UPDATE ON connections FROM quotation_worker")
    op.execute("REVOKE INSERT, UPDATE ON connections FROM quotation_app")
    op.execute(
        f"GRANT INSERT ({_APP_CONNECTION_INSERT_OLD}), UPDATE (status, updated_at, "
        "public_handle, public_handle_changed_at, config) ON connections TO quotation_app"
    )
    op.execute("REVOKE UPDATE (action_ref_id) ON outbound_messages FROM quotation_worker")
    op.execute("REVOKE INSERT ON outbound_messages FROM quotation_app")
    op.execute("REVOKE UPDATE (outbound_message_id) ON quotation_deliveries FROM quotation_app")
    op.execute("DROP POLICY approval_link_lookup ON approval_action_refs")

    for table in ("inbox_events", "jobs", "connection_events"):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute("DELETE FROM jobs WHERE kind IN ('classify_manager_reply', 'poll_connection')")
    op.drop_table("manager_reply_classifications")
    op.drop_table("approval_reply_prompts")
    op.execute(
        "DELETE FROM inbox_events WHERE event_type IN "
        "('manager_reply', 'customer_action', 'connection_update')"
    )
    op.execute("ALTER TABLE connection_events DISABLE TRIGGER connection_events_immutable")
    op.execute("DELETE FROM connection_events WHERE kind = 'resumed'")
    op.execute("ALTER TABLE connection_events ENABLE TRIGGER connection_events_immutable")
    for table in ("inbox_events", "jobs", "connection_events"):
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.drop_constraint("ck_connection_events_kind", "connection_events", type_="check")
    op.create_check_constraint(
        "ck_connection_events_kind",
        "connection_events",
        f"kind IN ({_CONNECTION_EVENT_KINDS_OLD})",
    )
    op.drop_constraint("ck_inbox_events_event_type", "inbox_events", type_="check")
    op.create_check_constraint(
        "ck_inbox_events_event_type", "inbox_events", f"event_type IN ({_EVENT_TYPES_OLD})"
    )
    op.drop_column("connections", "pending_action")
    op.drop_table("media_links")
    op.drop_index("ix_outbound_messages_action_ref", table_name="outbound_messages")
    op.drop_constraint("fk_outbound_messages_resent_from", "outbound_messages", type_="foreignkey")
    op.drop_constraint("fk_outbound_messages_action_ref", "outbound_messages", type_="foreignkey")
    op.drop_column("outbound_messages", "resent_from_id")
    op.drop_column("outbound_messages", "action_ref_id")
    op.drop_table("connection_routes")
