"""Catalogue copies from a business's ERP or shop (phase 6, ADR 0023).

- catalogue_sync_runs: one row per sync run of a product source (trigger, status, counts,
  the issues staff should fix, the error of a failed run, when the next run is due).
- catalogue_products, catalogue_prices and catalogue_stock accept source 'sync' next to
  'manual'; synced products carry the source's ID in external_id and the time in synced_at.
- The worker (which runs sync_catalogue) may now write the catalogue: insert categories,
  products, prices, stock counts and change records, and update the columns a sync changes.
  Prices, stock counts and change records stay append-only (reject_change triggers).
- Forced tenant RLS on the new table; the API role reads runs, the worker writes them.
- At most one waiting "Sync now" run per business: a partial unique index on jobs, so the API
  role still only inserts jobs and never reads the queue.

Downgrade drops the runs and their queued jobs; copied rows stay, relabelled 'manual'.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_catalogue_sync"
down_revision = "0013_provider_state"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_NOW = sa.text("now()")
_SOURCED = ("catalogue_products", "catalogue_prices", "catalogue_stock")
_PRODUCT_SYNC_COLUMNS = (
    "name, category_id, unit, minimum_quantity, quantity_step, search_terms, source, "
    "external_id, synced_at, archived_at, archived_by, row_version, updated_at, updated_by"
)
_CATEGORY_SYNC_COLUMNS = "archived_at, row_version, updated_at, updated_by"
_RUN_PROGRESS = "status, finished_at, counts, issues, error, next_run_at"
_MANUAL_SYNC = "kind = 'sync_catalogue' AND status = 'pending' AND payload->>'trigger' = 'manual'"


def upgrade() -> None:
    for table in _SOURCED:
        op.drop_constraint(f"ck_{table}_source", table, type_="check")
        op.create_check_constraint(f"ck_{table}_source", table, "source IN ('manual', 'sync')")

    op.create_table(
        "catalogue_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("counts", postgresql.JSONB(), nullable=True),
        sa.Column(
            "issues", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_catalogue_sync_runs"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_catalogue_sync_runs_tenant_id_tenants"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_id"],
            ["connections.tenant_id", "connections.id"],
            name="fk_catalogue_sync_runs_connection",
        ),
        sa.CheckConstraint(
            "trigger IN ('schedule', 'manual', 'connected')", name="ck_catalogue_sync_runs_trigger"
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name="ck_catalogue_sync_runs_status"
        ),
        sa.CheckConstraint(
            "(status = 'running') = (finished_at IS NULL)", name="ck_catalogue_sync_runs_finished"
        ),
    )
    op.create_index(
        "ix_catalogue_sync_runs_latest",
        "catalogue_sync_runs",
        ["tenant_id", "connection_id", sa.text("started_at DESC")],
    )
    op.execute("ALTER TABLE catalogue_sync_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE catalogue_sync_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON catalogue_sync_runs "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )

    op.execute("GRANT SELECT ON catalogue_sync_runs TO quotation_app")
    op.execute("GRANT SELECT, INSERT ON catalogue_sync_runs TO quotation_worker")
    op.execute(f"GRANT UPDATE ({_RUN_PROGRESS}) ON catalogue_sync_runs TO quotation_worker")
    op.create_index(
        "uq_jobs_manual_sync",
        "jobs",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text(_MANUAL_SYNC),
    )
    op.execute(
        "GRANT INSERT ON catalogue_categories, catalogue_products, catalogue_prices, "
        "catalogue_stock, catalogue_changes TO quotation_worker"
    )
    op.execute(f"GRANT UPDATE ({_PRODUCT_SYNC_COLUMNS}) ON catalogue_products TO quotation_worker")
    op.execute(
        f"GRANT UPDATE ({_CATEGORY_SYNC_COLUMNS}) ON catalogue_categories TO quotation_worker"
    )


def downgrade() -> None:
    op.execute(
        f"REVOKE UPDATE ({_CATEGORY_SYNC_COLUMNS}) ON catalogue_categories FROM quotation_worker"
    )
    op.execute(
        f"REVOKE UPDATE ({_PRODUCT_SYNC_COLUMNS}) ON catalogue_products FROM quotation_worker"
    )
    op.execute(
        "REVOKE INSERT ON catalogue_categories, catalogue_products, catalogue_prices, "
        "catalogue_stock, catalogue_changes FROM quotation_worker"
    )

    op.execute("ALTER TABLE jobs NO FORCE ROW LEVEL SECURITY")
    op.execute("DELETE FROM jobs WHERE kind = 'sync_catalogue'")
    op.execute("ALTER TABLE jobs FORCE ROW LEVEL SECURITY")
    op.drop_index("uq_jobs_manual_sync", table_name="jobs")
    op.drop_table("catalogue_sync_runs")

    # Copied rows stay as if typed in; history rows are relabelled with the trigger paused.
    for table in _SOURCED:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    for table in ("catalogue_prices", "catalogue_stock"):
        op.execute(f"ALTER TABLE {table} DISABLE TRIGGER {table}_immutable")
    for table in _SOURCED:
        op.execute(f"UPDATE {table} SET source = 'manual' WHERE source = 'sync'")
    for table in ("catalogue_prices", "catalogue_stock"):
        op.execute(f"ALTER TABLE {table} ENABLE TRIGGER {table}_immutable")
    for table in _SOURCED:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.drop_constraint(f"ck_{table}_source", table, type_="check")
        op.create_check_constraint(f"ck_{table}_source", table, "source IN ('manual')")
