"""Orders (phase 7, roadmap M6b, ADR 0024).

- orders: one per quotation (the purchase guard, Q4), copying the accepted version's totals
  and pointing at that exact version (tenant, quotation, version) and its content hash.
  fulfilment says where it is kept: local (staff move the status) or erp (written to the
  business's ERP once, then its status follows the ERP). Only status, hold reason, ERP
  customer, ERP order ID and updated_at ever change (column-level UPDATE grants).
- order_lines: the version's lines, copied exactly; immutable.
- order_events: append-only timeline (created, status changes, holds, ERP write results,
  reconciliation, staff resolutions, ignored ERP statuses); external events dedupe on
  (tenant, source, external_event_id).
- order_operations: the ERP write, intent before call (ADR 0004, 0015): a stable external
  reference unique per business and per connection, written before any call; status pending ->
  sending -> succeeded | failed | unknown | needs_attention.
- tenants.order_creation: staff (default, "Create order" button) or automatic (on acceptance).
- connections: one active order destination per business (like the product source).
- inbox_events accepts order_status_request ("where is my order?").
- Forced tenant RLS everywhere; both roles read and write what their jobs and screens need.

Downgrade deletes every order and its history, the order jobs and the new events.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_orders"
down_revision = "0014_catalogue_sync"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_NOW = sa.text("now()")
_TABLES = ("orders", "order_lines", "order_events", "order_operations")
_STATUSES = "'placed', 'confirmed', 'in_progress', 'shipped', 'delivered', 'cancelled', 'on_hold'"
_EVENT_TYPES = (
    "'created', 'status_changed', 'held', 'erp_write_succeeded', 'erp_write_failed', "
    "'erp_write_unknown', 'reconciled', 'needs_attention', 'resolved', 'retried', 'ignored'"
)
_OPERATION_STATUSES = "'pending', 'sending', 'succeeded', 'failed', 'unknown', 'needs_attention'"
_INBOX_OLD = (
    "'customer_message', 'manager_action', 'delivery_status', 'consent_change', "
    "'manager_reply', 'customer_action', 'connection_update'"
)
_INBOX_NEW = _INBOX_OLD + ", 'order_status_request'"
# The admin actions as of 0012, plus the order setting change.
_ADMIN_ACTIONS_V12 = (
    "'business_created', 'went_live', 'status_changed', 'details_changed', 'profile_changed', "
    "'logo_changed', 'pricing_changed', 'member_invited', 'invitation_resent', "
    "'invitation_revoked', 'invitation_accepted', 'member_roles_changed', 'member_removed', "
    "'api_key_created', 'api_key_revoked', 'contacts_merged', 'customer_messages_changed'"
)
_ORDER_JOBS = (
    "'create_order', 'erp_order_operation', 'reconcile_order_operation', "
    "'refresh_order_status', 'notify_order'"
)
_ORDER_PROGRESS = "status, hold_reason, erp_customer, erp_order_id, updated_at"
_OPERATION_PROGRESS = "status, erp_order_id, attempts, last_error, unknown_since, updated_at"


def _created() -> sa.Column[Any]:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False)


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], name=f"fk_{table}_tenant_id_tenants"
    )


def _order_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", "order_id"], ["orders.tenant_id", "orders.id"], name=f"fk_{table}_order"
    )


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "order_creation", sa.String(16), server_default=sa.text("'staff'"), nullable=False
        ),
    )
    op.create_check_constraint(
        "ck_tenants_order_creation", "tenants", "order_creation IN ('staff', 'automatic')"
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(16), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("hold_reason", sa.String(500), nullable=True),
        sa.Column("fulfilment", sa.String(8), nullable=False),
        sa.Column("erp_connection_id", sa.Uuid(), nullable=True),
        sa.Column("erp_customer", sa.String(140), nullable=True),
        sa.Column("erp_order_id", sa.String(140), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal", sa.Numeric(), nullable=False),
        sa.Column("tax", sa.Numeric(), nullable=False),
        sa.Column("total", sa.Numeric(), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        _created(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        _tenant_fk("orders"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            [
                "quotation_versions.tenant_id",
                "quotation_versions.quotation_id",
                "quotation_versions.version",
            ],
            name="fk_orders_version",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"], ["quotation_responses.id"], name="fk_orders_response"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "erp_connection_id"],
            ["connections.tenant_id", "connections.id"],
            name="fk_orders_connection",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_orders_tenant_id_id"),
        # One order per quotation, across all its versions (the purchase guard, Q4).
        sa.UniqueConstraint("tenant_id", "quotation_id", name="uq_orders_quotation"),
        sa.UniqueConstraint("tenant_id", "order_number", name="uq_orders_number"),
        sa.CheckConstraint(f"status IN ({_STATUSES})", name="ck_orders_status"),
        sa.CheckConstraint("fulfilment IN ('local', 'erp')", name="ck_orders_fulfilment"),
        sa.CheckConstraint(
            "(fulfilment = 'erp') = (erp_connection_id IS NOT NULL)", name="ck_orders_erp"
        ),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_orders_currency"),
    )
    op.create_index("ix_orders_status", "orders", ["tenant_id", "status", "created_at"])

    op.create_table(
        "order_lines",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("unit_price", sa.Numeric(), nullable=False),
        sa.Column("line_total", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "order_id", "line_index", name="pk_order_lines"),
        _tenant_fk("order_lines"),
        _order_fk("order_lines"),
        sa.CheckConstraint("quantity > 0", name="ck_order_lines_quantity"),
    )

    op.create_table(
        "order_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column(
            "detail", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("external_event_id", sa.String(200), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_order_events"),
        _tenant_fk("order_events"),
        _order_fk("order_events"),
        sa.CheckConstraint(f"type IN ({_EVENT_TYPES})", name="ck_order_events_type"),
        sa.CheckConstraint("source IN ('system', 'staff', 'erp')", name="ck_order_events_source"),
    )
    op.create_index(
        "ix_order_events_order", "order_events", ["tenant_id", "order_id", "occurred_at"]
    )
    op.create_index(
        "uq_order_events_external",
        "order_events",
        ["tenant_id", "source", "external_event_id"],
        unique=True,
        postgresql_where=sa.text("external_event_id IS NOT NULL"),
    )

    op.create_table(
        "order_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("external_reference", sa.String(64), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("erp_order_id", sa.String(140), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("unknown_since", sa.DateTime(timezone=True), nullable=True),
        _created(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_order_operations"),
        _tenant_fk("order_operations"),
        _order_fk("order_operations"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_id"],
            ["connections.tenant_id", "connections.id"],
            name="fk_order_operations_connection",
        ),
        sa.UniqueConstraint(
            "tenant_id", "external_reference", name="uq_order_operations_reference"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "connection_id",
            "external_reference",
            name="uq_order_operations_connection_reference",
        ),
        sa.CheckConstraint("kind IN ('create_sales_order')", name="ck_order_operations_kind"),
        sa.CheckConstraint(f"status IN ({_OPERATION_STATUSES})", name="ck_order_operations_status"),
        sa.CheckConstraint("attempts >= 0", name="ck_order_operations_attempts"),
    )
    op.create_index(
        "ix_order_operations_status", "order_operations", ["tenant_id", "status", "updated_at"]
    )

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
        )
    for table in ("order_lines", "order_events"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_change()"
        )
    for role in ("quotation_app", "quotation_worker"):
        op.execute(f"GRANT SELECT, INSERT ON {', '.join(_TABLES)} TO {role}")
        op.execute(f"GRANT UPDATE ({_ORDER_PROGRESS}) ON orders TO {role}")
        op.execute(f"GRANT UPDATE ({_OPERATION_PROGRESS}) ON order_operations TO {role}")
    op.execute("GRANT UPDATE (order_creation) ON tenants TO quotation_app")

    # One place a business's orders go, like its one product source.
    op.create_index(
        "uq_connections_one_orders",
        "connections",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND purposes @> ARRAY['orders']::text[]"),
    )
    op.drop_constraint("ck_inbox_events_event_type", "inbox_events", type_="check")
    op.create_check_constraint(
        "ck_inbox_events_event_type", "inbox_events", f"event_type IN ({_INBOX_NEW})"
    )
    op.drop_constraint("ck_admin_events_action", "admin_events", type_="check")
    op.create_check_constraint(
        "ck_admin_events_action",
        "admin_events",
        f"action IN ({_ADMIN_ACTIONS_V12}, 'order_settings_changed')",
    )


def downgrade() -> None:
    for table in ("inbox_events", "jobs", "admin_events"):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"DELETE FROM jobs WHERE kind IN ({_ORDER_JOBS})")
    op.execute("DELETE FROM inbox_events WHERE event_type = 'order_status_request'")
    op.execute("ALTER TABLE admin_events DISABLE TRIGGER admin_events_immutable")
    op.execute("DELETE FROM admin_events WHERE action = 'order_settings_changed'")
    op.execute("ALTER TABLE admin_events ENABLE TRIGGER admin_events_immutable")
    for table in ("inbox_events", "jobs", "admin_events"):
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.drop_constraint("ck_admin_events_action", "admin_events", type_="check")
    op.create_check_constraint(
        "ck_admin_events_action", "admin_events", f"action IN ({_ADMIN_ACTIONS_V12})"
    )
    op.drop_constraint("ck_inbox_events_event_type", "inbox_events", type_="check")
    op.create_check_constraint(
        "ck_inbox_events_event_type", "inbox_events", f"event_type IN ({_INBOX_OLD})"
    )
    op.drop_index("uq_connections_one_orders", table_name="connections")
    op.execute("REVOKE UPDATE (order_creation) ON tenants FROM quotation_app")
    for table in reversed(_TABLES):
        op.drop_table(table)
    op.drop_constraint("ck_tenants_order_creation", "tenants", type_="check")
    op.drop_column("tenants", "order_creation")
