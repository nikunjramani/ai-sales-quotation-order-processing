"""Add portal sessions, quotations, immutable versions, approvals and channel bindings.

Security notes:
- quotation_versions and approval_decisions are append-only. No role is granted UPDATE or
  DELETE, and a trigger rejects changes even from the owner.
- user_sessions has no tenant (a person may belong to several tenants). Like API keys, the API
  role sees only the row whose token hash it presents.
- Two narrow lookups let the API list a signed-in person's own memberships and tenant names
  (app.subject); everything else stays behind forced tenant RLS.
- Column-level UPDATE grants limit which fields each role may change.
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import SchemaItem

revision = "0005_approvals"
down_revision = "0004_workflow"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_SUBJECT = "NULLIF(current_setting('app.subject', true), '')"
_OLD_RUN_STATUSES = (
    "status IN ('running', 'ready_for_quotation', 'needs_clarification', 'needs_review')"
)
_NEW_RUN_STATUSES = (
    "status IN ('running', 'ready_for_quotation', 'needs_clarification', 'needs_review', "
    "'approved', 'rejected')"
)
_TABLES = (
    "quotations",
    "quotation_versions",
    "approval_tasks",
    "approval_decisions",
    "channel_enrollments",
    "channel_bindings",
    "approval_action_refs",
)


def _now() -> sa.TextClause:
    return sa.text("now()")


def _id_columns(table: str) -> list[SchemaItem]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=f"fk_{table}_tenant_id_tenants"
        ),
    ]


def _created() -> sa.Column[datetime]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False
    )


def upgrade() -> None:
    op.drop_constraint("ck_workflow_runs_status", "workflow_runs", type_="check")
    op.create_check_constraint("ck_workflow_runs_status", "workflow_runs", _NEW_RUN_STATUSES)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_sha256", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        _created(),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.UniqueConstraint("token_sha256", name="uq_user_sessions_token_sha256"),
    )
    op.create_table(
        "quotations",
        *_id_columns("quotations"),
        sa.Column("enquiry_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=True),
        sa.Column("pricing_issues", postgresql.JSONB(), nullable=True),
        _created(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enquiry_id"],
            ["enquiries.tenant_id", "enquiries.id"],
            name="fk_quotations_enquiry",
        ),
        sa.UniqueConstraint("tenant_id", "enquiry_id", name="uq_quotations_tenant_enquiry"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_quotations_tenant_id_id"),
        sa.CheckConstraint(
            "status IN ('pricing_failed', 'pending_approval', 'revision_requested', "
            "'revision_submitted', 'approved', 'rejected')",
            name="ck_quotations_status",
        ),
    )
    op.create_table(
        "quotation_versions",
        *_id_columns("quotation_versions"),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("total", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("command_id", sa.Uuid(), nullable=True),
        _created(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "quotation_id"],
            ["quotations.tenant_id", "quotations.id"],
            name="fk_quotation_versions_quotation",
        ),
        sa.UniqueConstraint(
            "tenant_id", "quotation_id", "version", name="uq_quotation_versions_number"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_quotation_versions_tenant_id_id"),
        sa.UniqueConstraint("tenant_id", "command_id", name="uq_quotation_versions_command"),
        sa.CheckConstraint("version >= 1", name="ck_quotation_versions_version"),
    )
    op.create_table(
        "approval_tasks",
        *_id_columns("approval_tasks"),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        _created(),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id", "version_id"],
            ["quotation_versions.tenant_id", "quotation_versions.id"],
            name="fk_approval_tasks_version",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "quotation_id"],
            ["quotations.tenant_id", "quotations.id"],
            name="fk_approval_tasks_quotation",
        ),
        sa.UniqueConstraint("tenant_id", "version_id", name="uq_approval_tasks_version"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_approval_tasks_tenant_id_id"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'revision_requested')",
            name="ck_approval_tasks_status",
        ),
    )
    op.create_table(
        "approval_decisions",
        *_id_columns("approval_decisions"),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("actor_subject", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("transport", sa.String(32), nullable=False),
        sa.Column("evidence_ref", sa.String(300), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "task_id"],
            ["approval_tasks.tenant_id", "approval_tasks.id"],
            name="fk_approval_decisions_task",
        ),
        sa.UniqueConstraint("tenant_id", "task_id", name="uq_approval_decisions_task"),
        sa.UniqueConstraint("tenant_id", "command_id", name="uq_approval_decisions_command"),
        sa.CheckConstraint(
            "action IN ('approve', 'reject', 'request_revision')",
            name="ck_approval_decisions_action",
        ),
    )
    op.create_table(
        "channel_enrollments",
        *_id_columns("channel_enrollments"),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("code_sha256", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        _created(),
        sa.UniqueConstraint("tenant_id", "code_sha256", name="uq_channel_enrollments_code"),
    )
    op.create_table(
        "channel_bindings",
        *_id_columns("channel_bindings"),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("connection_id", sa.String(100), nullable=False),
        sa.Column("external_user_id", sa.String(200), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        _created(),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "id", name="uq_channel_bindings_tenant_id_id"),
    )
    op.create_index(
        "uq_channel_bindings_active_account",
        "channel_bindings",
        ["tenant_id", "channel", "connection_id", "external_user_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "approval_action_refs",
        *_id_columns("approval_action_refs"),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=False),
        sa.Column("token_sha256", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        _created(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "task_id"],
            ["approval_tasks.tenant_id", "approval_tasks.id"],
            name="fk_approval_action_refs_task",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "binding_id"],
            ["channel_bindings.tenant_id", "channel_bindings.id"],
            name="fk_approval_action_refs_binding",
        ),
        sa.UniqueConstraint(
            "tenant_id", "task_id", "binding_id", name="uq_approval_action_refs_task"
        ),
        sa.UniqueConstraint("token_sha256", name="uq_approval_action_refs_token"),
    )

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
        )

    # Append-only audit tables: reject UPDATE and DELETE from every role, including the owner.
    op.execute(
        "CREATE FUNCTION reject_change() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION '% rows are immutable', TG_TABLE_NAME; END $$"
    )
    for table in ("quotation_versions", "approval_decisions"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_change()"
        )

    # Sessions: the API role sees only the row whose token hash it presents.
    session_match = "token_sha256 = NULLIF(current_setting('app.session_token_sha256', true), '')"
    op.execute("ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_sessions FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY session_lookup ON user_sessions FOR SELECT TO quotation_app "
        f"USING ({session_match})"
    )
    op.execute(
        f"CREATE POLICY session_revoke ON user_sessions FOR UPDATE TO quotation_app "
        f"USING ({session_match}) WITH CHECK ({session_match})"
    )
    op.execute(
        "CREATE POLICY session_create ON user_sessions FOR INSERT TO quotation_app "
        "WITH CHECK (true)"
    )
    # A signed-in person may list their own memberships and those tenants' names.
    op.execute(
        f"CREATE POLICY membership_self_lookup ON memberships FOR SELECT TO quotation_app "
        f"USING (subject = {_SUBJECT})"
    )
    op.execute(
        "CREATE POLICY tenant_member_lookup ON tenants FOR SELECT TO quotation_app "
        "USING (EXISTS (SELECT 1 FROM memberships m "
        f"WHERE m.tenant_id = tenants.id AND m.subject = {_SUBJECT}))"
    )

    # API role: reads, decisions, revisions, enrollment and binding management.
    op.execute("GRANT SELECT, INSERT, UPDATE (revoked_at) ON user_sessions TO quotation_app")
    op.execute(
        "GRANT SELECT, UPDATE (status, current_version, updated_at) ON quotations TO quotation_app"
    )
    op.execute("GRANT SELECT, INSERT ON quotation_versions, approval_decisions TO quotation_app")
    op.execute("GRANT SELECT, UPDATE (status, decided_at) ON approval_tasks TO quotation_app")
    op.execute("GRANT SELECT, INSERT, UPDATE (consumed_at) ON channel_enrollments TO quotation_app")
    op.execute("GRANT SELECT, INSERT, UPDATE (revoked_at) ON channel_bindings TO quotation_app")
    op.execute("GRANT SELECT, UPDATE (consumed_at) ON approval_action_refs TO quotation_app")
    # Worker role: drafting, approval tasks, notifications and pricing inputs.
    op.execute("GRANT SELECT ON tenants, memberships, tenant_pricing_policies TO quotation_worker")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (status, current_version, pricing_issues, updated_at) "
        "ON quotations TO quotation_worker"
    )
    op.execute("GRANT SELECT, INSERT ON quotation_versions, approval_tasks TO quotation_worker")
    op.execute("GRANT SELECT ON approval_decisions, channel_bindings TO quotation_worker")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (token_sha256, expires_at, sent_at) "
        "ON approval_action_refs TO quotation_worker"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE SELECT ON tenants, memberships, tenant_pricing_policies FROM quotation_worker"
    )
    op.execute("DROP POLICY tenant_member_lookup ON tenants")
    op.execute("DROP POLICY membership_self_lookup ON memberships")
    for table in reversed(_TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION reject_change()")
    op.drop_table("user_sessions")
    op.drop_constraint("ck_workflow_runs_status", "workflow_runs", type_="check")
    # Approval workflow runs, their checkpoints and jobs have no meaning before M4; remove
    # them. FORCE RLS hides rows from the owner too, so lift it inside this transaction only.
    op.execute("ALTER TABLE workflow_runs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE jobs NO FORCE ROW LEVEL SECURITY")
    approval_threads = (
        "SELECT id::text FROM workflow_runs WHERE graph_version LIKE 'quotation-approval-%'"
    )
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        op.execute(f"DELETE FROM {table} WHERE thread_id IN ({approval_threads})")
    op.execute("DELETE FROM workflow_runs WHERE graph_version LIKE 'quotation-approval-%'")
    op.execute(
        "DELETE FROM jobs WHERE kind IN ('draft_quotation', 'notify_approvers', 'resume_quotation')"
    )
    op.execute("ALTER TABLE jobs FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workflow_runs FORCE ROW LEVEL SECURITY")
    op.create_check_constraint("ck_workflow_runs_status", "workflow_runs", _OLD_RUN_STATUSES)
