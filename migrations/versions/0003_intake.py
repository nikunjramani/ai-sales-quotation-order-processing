"""Add API keys, inbox events, enquiries, attachments and the durable job queue.

Requires the quotation_worker role (infra/postgres/init.sql). All tables use forced tenant RLS.
Exceptions, both narrow: the API role may read one API key row whose ID it presents, and the
worker role may see the job queue across tenants (only jobs, nothing else).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_intake"
down_revision = "0002_memberships_policies"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_ROLE_CHECK = "role IN ('administrator', 'sales_operator', 'approver', 'viewer', 'intake_service')"


def _now() -> sa.TextClause:
    return sa.text("now()")


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], name=f"fk_{table}_tenant_id_tenants"
    )


def _isolate(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("secret_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_api_keys"),
        _tenant_fk("api_keys"),
        sa.CheckConstraint(_ROLE_CHECK, name="ck_api_keys_role"),
    )
    op.create_table(
        "inbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("connection_id", sa.String(100), nullable=False),
        sa.Column("provider_event_id", sa.String(200), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("envelope", postgresql.JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_inbox_events"),
        _tenant_fk("inbox_events"),
        sa.UniqueConstraint(
            "tenant_id",
            "channel",
            "connection_id",
            "provider_event_id",
            name="uq_inbox_events_provider_event",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_inbox_events_tenant_id_id"),
    )
    op.create_table(
        "enquiries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("inbox_event_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("customer_reference", sa.String(200), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_enquiries"),
        _tenant_fk("enquiries"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "inbox_event_id"],
            ["inbox_events.tenant_id", "inbox_events.id"],
            name="fk_enquiries_inbox_event",
        ),
        sa.UniqueConstraint("inbox_event_id", name="uq_enquiries_inbox_event_id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_enquiries_tenant_id_id"),
        sa.CheckConstraint(
            "status IN ('received', 'ready_for_extraction', 'needs_review')",
            name="ck_enquiries_status",
        ),
    )
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("enquiry_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("declared_content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("detected_content_type", sa.String(100), nullable=True),
        sa.Column("rejection_reason", sa.String(50), nullable=True),
        sa.Column("storage_key", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_attachments"),
        _tenant_fk("attachments"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enquiry_id"],
            ["enquiries.tenant_id", "enquiries.id"],
            name="fk_attachments_enquiry",
        ),
        sa.CheckConstraint(
            "status IN ('quarantined', 'clean', 'rejected')", name="ck_attachments_status"
        ),
    )
    op.create_index("ix_attachments_tenant_enquiry", "attachments", ["tenant_id", "enquiry_id"])
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        _tenant_fk("jobs"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'dead')", name="ck_jobs_status"
        ),
        sa.CheckConstraint("attempts >= 0 AND max_attempts >= 1", name="ck_jobs_attempts"),
    )
    op.create_index("ix_jobs_claim", "jobs", ["status", "run_at"])

    for table in ("api_keys", "inbox_events", "enquiries", "attachments", "jobs"):
        _isolate(table)
    # Authentication must find a key before the tenant is known. This policy reveals only the
    # row whose ID the caller supplied; the secret hash must still match.
    op.execute(
        "CREATE POLICY api_key_lookup ON api_keys FOR SELECT TO quotation_app "
        "USING (id = NULLIF(current_setting('app.api_key_id', true), '')::uuid)"
    )
    op.execute(
        "CREATE POLICY worker_queue ON jobs TO quotation_worker USING (true) WITH CHECK (true)"
    )

    op.execute("GRANT SELECT ON api_keys TO quotation_app")
    op.execute("GRANT SELECT, INSERT ON inbox_events, enquiries, attachments TO quotation_app")
    op.execute("GRANT INSERT ON jobs TO quotation_app")
    op.execute("GRANT SELECT ON inbox_events TO quotation_worker")
    op.execute("GRANT SELECT, UPDATE ON enquiries, attachments, jobs TO quotation_worker")


def downgrade() -> None:
    for table in ("jobs", "attachments", "enquiries", "inbox_events", "api_keys"):
        op.drop_table(table)
