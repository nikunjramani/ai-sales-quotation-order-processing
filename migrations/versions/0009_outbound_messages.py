"""One outbox for everything we send (phase 1, ADR 0018).

- outbound_messages: one row per message (quotation to a customer, approval request or notice
  to a manager): connection, template, IDs-only parameters, the rendered fixed wording (never
  a single-use action token), recipient, idempotency key (unique per business), status
  (pending, sending, available, sent, delivered, failed, unknown), provider message ID, links
  to the quotation, task, binding, enquiry and response. Forced tenant RLS.
- quotation_deliveries.outbound_message_id: the message that carries a delivery out; the
  delivery's status mirrors the message's.

Backfill: one message per existing delivery (same status, connection from the enquiry's inbox
event). Past approval requests and notices had no outbox and are not backfilled.
Downgrade: re-queues deliver_quotation / notify_approvers for work still pending, deletes
send_message jobs and drops the table.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_outbound_messages"
down_revision = "0008_connections"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_STATUSES = "'pending', 'sending', 'available', 'sent', 'delivered', 'failed', 'unknown'"
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "outbound_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_ref", sa.Uuid(), nullable=False),
        sa.Column("provider_key", sa.String(32), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("template_key", sa.String(64), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("recipient", sa.String(200), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provider_message_id", sa.String(200), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("quotation_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("approval_task_id", sa.Uuid(), nullable=True),
        sa.Column("binding_id", sa.Uuid(), nullable=True),
        sa.Column("enquiry_id", sa.Uuid(), nullable=True),
        sa.Column("response_id", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_outbound_messages"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_outbound_messages_tenant_id_tenants"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_ref"],
            ["connections.tenant_id", "connections.id"],
            name="fk_outbound_messages_connection",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            ["quotation_documents.tenant_id", "quotation_documents.id"],
            name="fk_outbound_messages_document",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_outbound_messages_tenant_id_id"),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_outbound_messages_idempotency"
        ),
        sa.CheckConstraint(f"status IN ({_STATUSES})", name="ck_outbound_messages_status"),
    )
    op.create_index(
        "uq_outbound_messages_provider_message",
        "outbound_messages",
        ["tenant_id", "connection_ref", "provider_message_id"],
        unique=True,
        postgresql_where=sa.text("provider_message_id IS NOT NULL"),
    )
    op.create_index("ix_outbound_messages_status", "outbound_messages", ["tenant_id", "status"])
    op.create_index(
        "ix_outbound_messages_quotation", "outbound_messages", ["tenant_id", "quotation_id"]
    )
    op.create_index(
        "ix_outbound_messages_task", "outbound_messages", ["tenant_id", "approval_task_id"]
    )
    op.execute("ALTER TABLE outbound_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE outbound_messages FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON outbound_messages "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )

    op.add_column(
        "quotation_deliveries", sa.Column("outbound_message_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_quotation_deliveries_message",
        "quotation_deliveries",
        "outbound_messages",
        ["tenant_id", "outbound_message_id"],
        ["tenant_id", "id"],
    )
    op.create_unique_constraint(
        "uq_quotation_deliveries_message", "quotation_deliveries", ["outbound_message_id"]
    )

    _backfill()

    op.execute("GRANT SELECT ON outbound_messages TO quotation_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (status, provider_message_id, last_error, updated_at, "
        "sent_at, delivered_at) ON outbound_messages TO quotation_worker"
    )
    op.execute("GRANT UPDATE (outbound_message_id) ON quotation_deliveries TO quotation_worker")


def _backfill() -> None:
    tables = (
        "outbound_messages",
        "quotation_deliveries",
        "quotations",
        "enquiries",
        "inbox_events",
    )
    for table in tables:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(
        "INSERT INTO outbound_messages (id, tenant_id, connection_ref, provider_key, purpose, "
        "template_key, params, body_text, metadata, recipient, idempotency_key, status, "
        "provider_message_id, last_error, document_id, quotation_id, version, enquiry_id, "
        "correlation_id, created_at, updated_at, sent_at) "
        "SELECT gen_random_uuid(), d.tenant_id, e.connection_ref, d.channel, "
        "'customer_messages', 'quotation_document', "
        "jsonb_build_object('delivery_id', d.id::text), '', "
        "jsonb_build_object('version', d.version::text), d.recipient, "
        "'quotation-delivery:' || d.id, d.status, d.provider_reference, d.last_error, "
        "d.document_id, d.quotation_id, d.version, q.enquiry_id, n.correlation_id, "
        "d.created_at, d.updated_at, d.delivered_at "
        "FROM quotation_deliveries d "
        "JOIN quotations q ON q.tenant_id = d.tenant_id AND q.id = d.quotation_id "
        "JOIN enquiries n ON n.tenant_id = q.tenant_id AND n.id = q.enquiry_id "
        "JOIN inbox_events e ON e.tenant_id = n.tenant_id AND e.id = n.inbox_event_id"
    )
    op.execute(
        "UPDATE quotation_deliveries d SET outbound_message_id = m.id FROM outbound_messages m "
        "WHERE m.tenant_id = d.tenant_id AND m.idempotency_key = 'quotation-delivery:' || d.id"
    )
    for table in tables:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (outbound_message_id) ON quotation_deliveries FROM quotation_worker")
    tables = (
        "jobs",
        "quotation_deliveries",
        "approval_tasks",
        "approval_action_refs",
        "quotations",
    )
    for table in tables:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    # Work the outbox would still have done goes back to the old jobs.
    op.execute(
        "INSERT INTO jobs (id, tenant_id, kind, payload, status, max_attempts, run_at, "
        "correlation_id) SELECT gen_random_uuid(), d.tenant_id, 'deliver_quotation', "
        "jsonb_build_object('delivery_id', d.id::text), 'pending', 5, now(), "
        "gen_random_uuid() FROM quotation_deliveries d WHERE d.status = 'pending'"
    )
    op.execute(
        "INSERT INTO jobs (id, tenant_id, kind, payload, status, max_attempts, run_at, "
        "correlation_id) SELECT gen_random_uuid(), t.tenant_id, 'notify_approvers', "
        "jsonb_build_object('task_id', t.id::text), 'pending', 5, now(), gen_random_uuid() "
        "FROM approval_tasks t WHERE t.status = 'pending' AND NOT EXISTS (SELECT 1 FROM "
        "approval_action_refs r WHERE r.tenant_id = t.tenant_id AND r.task_id = t.id "
        "AND r.sent_at IS NOT NULL)"
    )
    op.execute("DELETE FROM jobs WHERE kind = 'send_message'")
    for table in tables:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.drop_constraint("uq_quotation_deliveries_message", "quotation_deliveries", type_="unique")
    op.drop_constraint(
        "fk_quotation_deliveries_message", "quotation_deliveries", type_="foreignkey"
    )
    op.drop_column("quotation_deliveries", "outbound_message_id")
    op.drop_table("outbound_messages")
