"""Add quotation documents (approved PDFs) and the customer delivery outbox.

Security notes:
- quotation_documents is append-only: no role may UPDATE or DELETE, and the reject_change()
  trigger from 0005 blocks changes even from the owner.
- quotation_deliveries is tenant-isolated like every business table. Column-level grants let
  the worker change only delivery progress and the API only record the first download.
- The PDF bytes live in private object storage, not in the database; downgrading leaves those
  files behind (they are unreachable without these rows and can be deleted by an operator).
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_documents"
down_revision = "0005_approvals"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_TABLES = ("quotation_documents", "quotation_deliveries")
_NOW = sa.text("now()")
_VERSION_COLUMNS = [
    "quotation_versions.tenant_id",
    "quotation_versions.quotation_id",
    "quotation_versions.version",
]


def upgrade() -> None:
    op.create_table(
        "quotation_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(200), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("renderer", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_quotation_documents"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_quotation_documents_tenant_id_tenants"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            _VERSION_COLUMNS,
            name="fk_quotation_documents_version",
        ),
        sa.UniqueConstraint(
            "tenant_id", "quotation_id", "version", "kind", name="uq_quotation_documents_version"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_quotation_documents_tenant_id_id"),
        sa.CheckConstraint("kind IN ('approved')", name="ck_quotation_documents_kind"),
        sa.CheckConstraint("size_bytes > 0", name="ck_quotation_documents_size"),
    )
    op.create_table(
        "quotation_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("recipient", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("provider_reference", sa.String(200), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_quotation_deliveries"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_quotation_deliveries_tenant_id_tenants"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            _VERSION_COLUMNS,
            name="fk_quotation_deliveries_version",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            ["quotation_documents.tenant_id", "quotation_documents.id"],
            name="fk_quotation_deliveries_document",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "quotation_id",
            "version",
            "channel",
            "recipient",
            name="uq_quotation_deliveries_target",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'available', 'sent', 'failed', 'unknown')",
            name="ck_quotation_deliveries_status",
        ),
    )
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
        )
    op.execute(
        "CREATE TRIGGER quotation_documents_immutable BEFORE UPDATE OR DELETE "
        "ON quotation_documents FOR EACH ROW EXECUTE FUNCTION reject_change()"
    )

    # Worker: render and store documents, queue and progress deliveries.
    op.execute("GRANT SELECT, INSERT ON quotation_documents TO quotation_worker")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (status, document_id, provider_reference, last_error, "
        "updated_at, delivered_at) ON quotation_deliveries TO quotation_worker"
    )
    # API: portal reads, customer downloads (records only the first download time).
    op.execute("GRANT SELECT ON quotation_documents TO quotation_app")
    op.execute(
        "GRANT SELECT, UPDATE (first_downloaded_at) ON quotation_deliveries TO quotation_app"
    )


def downgrade() -> None:
    op.drop_table("quotation_deliveries")
    op.drop_table("quotation_documents")
    # Delivery jobs have no meaning before M5. FORCE RLS hides rows from the owner too, so lift
    # it inside this transaction only.
    op.execute("ALTER TABLE jobs NO FORCE ROW LEVEL SECURITY")
    op.execute("DELETE FROM jobs WHERE kind = 'deliver_quotation'")
    op.execute("ALTER TABLE jobs FORCE ROW LEVEL SECURITY")
