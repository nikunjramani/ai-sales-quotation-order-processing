"""Add workflow runs, LangGraph checkpoint tables and the M3 enquiry statuses.

Checkpoint tables use LangGraph's own schema, copied here and frozen so this migration never
changes when the library is upgraded. `CONCURRENTLY` is removed because migrations run inside
a transaction (the tables are new and empty). Versions 0-9 are recorded in
checkpoint_migrations, so the library's setup() has nothing left to do. A unit test fails if a
future library version adds migrations, prompting a new Alembic migration.

Checkpoints hold workflow progress and have no tenant column: only the worker role may access
them, and it opens a thread only through a tenant-scoped workflow_runs row.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_workflow"
down_revision = "0003_intake"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_OLD_STATUSES = "status IN ('received', 'ready_for_extraction', 'needs_review')"
_NEW_STATUSES = (
    "status IN ('received', 'ready_for_extraction', 'needs_review', "
    "'ready_for_quotation', 'needs_clarification')"
)

# Frozen copy of langgraph-checkpoint-postgres BasePostgresSaver.MIGRATIONS (3.2.0), index = v.
LANGGRAPH_CHECKPOINT_MIGRATIONS = (
    """CREATE TABLE IF NOT EXISTS checkpoint_migrations (
    v INTEGER PRIMARY KEY
);""",
    """CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);""",
    """CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);""",
    """CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);""",
    "ALTER TABLE checkpoint_blobs ALTER COLUMN blob DROP not null;",
    "SELECT 1;",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoints_thread_id_idx ON checkpoints(thread_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoint_blobs_thread_id_idx "
    "ON checkpoint_blobs(thread_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoint_writes_thread_id_idx "
    "ON checkpoint_writes(thread_id);",
    "ALTER TABLE checkpoint_writes ADD COLUMN IF NOT EXISTS task_path TEXT NOT NULL DEFAULT '';",
)
_CHECKPOINT_TABLES = "checkpoint_migrations, checkpoints, checkpoint_blobs, checkpoint_writes"


def upgrade() -> None:
    op.drop_constraint("ck_enquiries_status", "enquiries", type_="check")
    op.create_check_constraint("ck_enquiries_status", "enquiries", _NEW_STATUSES)

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("enquiry_id", sa.Uuid(), nullable=False),
        sa.Column("graph_version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("outcome", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_runs"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_workflow_runs_tenant_id_tenants"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enquiry_id"],
            ["enquiries.tenant_id", "enquiries.id"],
            name="fk_workflow_runs_enquiry",
        ),
        sa.UniqueConstraint(
            "tenant_id", "enquiry_id", "graph_version", name="uq_workflow_runs_enquiry_version"
        ),
        sa.CheckConstraint(
            "status IN ('running', 'ready_for_quotation', 'needs_clarification', 'needs_review')",
            name="ck_workflow_runs_status",
        ),
    )
    op.execute("ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workflow_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON workflow_runs "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )
    op.execute("GRANT SELECT ON workflow_runs TO quotation_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON workflow_runs TO quotation_worker")
    # The worker queues follow-up jobs (preparation -> extraction) in the same transaction.
    op.execute("GRANT INSERT ON jobs TO quotation_worker")

    for version, statement in enumerate(LANGGRAPH_CHECKPOINT_MIGRATIONS):
        op.execute(statement.replace("CONCURRENTLY ", ""))
        op.execute(f"INSERT INTO checkpoint_migrations (v) VALUES ({version})")
    op.execute(f"REVOKE ALL ON {_CHECKPOINT_TABLES} FROM PUBLIC")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {_CHECKPOINT_TABLES} TO quotation_worker")


def downgrade() -> None:
    op.execute(f"DROP TABLE {_CHECKPOINT_TABLES}")
    op.execute("REVOKE INSERT ON jobs FROM quotation_worker")
    op.drop_table("workflow_runs")
    op.drop_constraint("ck_enquiries_status", "enquiries", type_="check")
    # Rows in M3-only states cannot be represented before M3; send them to manual review.
    # FORCE RLS hides all rows from the owner too, so lift it inside this transaction only.
    op.execute("ALTER TABLE enquiries NO FORCE ROW LEVEL SECURITY")
    op.execute(
        "UPDATE enquiries SET status = 'needs_review' "
        "WHERE status IN ('ready_for_quotation', 'needs_clarification')"
    )
    op.execute("ALTER TABLE enquiries FORCE ROW LEVEL SECURITY")
    op.create_check_constraint("ck_enquiries_status", "enquiries", _OLD_STATUSES)
