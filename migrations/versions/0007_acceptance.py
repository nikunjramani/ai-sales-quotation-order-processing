"""Customer acceptance (M6, ADR 0016): validity, responses, new statuses.

- tenant_pricing_policies.quote_validity_days: days an issued quotation can be answered
  (default 7, user decision), counted from delivery.
- quotation_documents.valid_until: printed on the PDF. Existing M5 documents get
  created_at + 7 days (the trigger that keeps documents immutable is paused for that one update).
- quotation_responses: append-only answers (accept/decline/refused-because-prices-changed,
  staff withdrawal, expiry). One closing outcome per quotation (partial unique index).
- New quotation and workflow-run statuses: accepted, declined, expired, withdrawn.

Downgrade maps the new statuses back to 'approved' and removes M6 jobs. Approval runs paused
while waiting for the customer cannot resume on M5 code (their graph step no longer exists).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_acceptance"
down_revision = "0006_documents"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_NEW = "'accepted', 'declined', 'expired', 'withdrawn'"
_QUOTATION_STATUSES = (
    "'pricing_failed', 'pending_approval', 'revision_requested', 'revision_submitted', "
    "'approved', 'rejected'"
)
_RUN_STATUSES = (
    "'running', 'ready_for_quotation', 'needs_clarification', 'needs_review', 'approved', "
    "'rejected'"
)


def _status_checks(extra: str) -> None:
    for table, name, statuses in (
        ("quotations", "ck_quotations_status", _QUOTATION_STATUSES),
        ("workflow_runs", "ck_workflow_runs_status", _RUN_STATUSES),
    ):
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, f"status IN ({statuses}{extra})")


def upgrade() -> None:
    op.add_column(
        "tenant_pricing_policies",
        sa.Column("quote_validity_days", sa.Integer(), server_default=sa.text("7"), nullable=False),
    )
    op.create_check_constraint(
        "ck_tenant_pricing_policies_quote_validity",
        "tenant_pricing_policies",
        "quote_validity_days >= 1",
    )

    op.add_column(
        "quotation_documents", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True)
    )
    # FORCE RLS hides rows from the owner too, and documents are immutable; lift both for this
    # one backfill inside the migration transaction.
    op.execute("ALTER TABLE quotation_documents NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE quotation_documents DISABLE TRIGGER quotation_documents_immutable")
    op.execute("UPDATE quotation_documents SET valid_until = created_at + interval '7 days'")
    op.execute("ALTER TABLE quotation_documents ENABLE TRIGGER quotation_documents_immutable")
    op.execute("ALTER TABLE quotation_documents FORCE ROW LEVEL SECURITY")
    op.alter_column("quotation_documents", "valid_until", nullable=False)

    _status_checks(f", {_NEW}")

    op.create_table(
        "quotation_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("differences", postgresql.JSONB(), nullable=False),
        sa.Column("revised_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_quotation_responses"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_quotation_responses_tenant_id_tenants"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            [
                "quotation_versions.tenant_id",
                "quotation_versions.quotation_id",
                "quotation_versions.version",
            ],
            name="fk_quotation_responses_version",
        ),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_quotation_responses_key"),
        sa.CheckConstraint(
            "outcome IN ('accepted', 'declined', 'refused_changed', 'withdrawn', 'expired')",
            name="ck_quotation_responses_outcome",
        ),
    )
    op.create_index(
        "uq_quotation_responses_closing",
        "quotation_responses",
        ["tenant_id", "quotation_id"],
        unique=True,
        postgresql_where=sa.text("outcome <> 'refused_changed'"),
    )
    op.execute("ALTER TABLE quotation_responses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE quotation_responses FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON quotation_responses "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )
    op.execute(
        "CREATE TRIGGER quotation_responses_immutable BEFORE UPDATE OR DELETE "
        "ON quotation_responses FOR EACH ROW EXECUTE FUNCTION reject_change()"
    )
    # API: customer answers and staff withdrawal; a refused acceptance may store pricing issues.
    op.execute("GRANT SELECT, INSERT ON quotation_responses TO quotation_app")
    op.execute("GRANT UPDATE (pricing_issues) ON quotations TO quotation_app")
    # Worker: expiry and reading answers when the workflow resumes.
    op.execute("GRANT SELECT, INSERT ON quotation_responses TO quotation_worker")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (pricing_issues) ON quotations FROM quotation_app")
    op.drop_table("quotation_responses")
    for table in ("quotations", "workflow_runs", "jobs"):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"UPDATE quotations SET status = 'approved' WHERE status IN ({_NEW})")
    op.execute(f"UPDATE workflow_runs SET status = 'approved' WHERE status IN ({_NEW})")
    op.execute("DELETE FROM jobs WHERE kind IN ('expire_quotation', 'notify_response')")
    for table in ("quotations", "workflow_runs", "jobs"):
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    _status_checks("")
    op.drop_column("quotation_documents", "valid_until")
    op.drop_constraint(
        "ck_tenant_pricing_policies_quote_validity", "tenant_pricing_policies", type_="check"
    )
    op.drop_column("tenant_pricing_policies", "quote_validity_days")
