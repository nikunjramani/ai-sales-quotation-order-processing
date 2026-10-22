"""Add tenant memberships and pricing policies, both behind forced row-level security."""

import sqlalchemy as sa
from alembic import op

revision = "0002_memberships_policies"
down_revision = "0001_tenants"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _protect(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )
    # Runtime may read only; memberships and policies are changed by owner/admin paths.
    op.execute(f"GRANT SELECT ON {table} TO quotation_app")


def upgrade() -> None:
    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_memberships_tenant_id_tenants"
        ),
        sa.UniqueConstraint(
            "tenant_id", "subject", "role", name="uq_memberships_tenant_subject_role"
        ),
        sa.CheckConstraint(
            "role IN ('administrator', 'sales_operator', 'approver', 'viewer')",
            name="ck_memberships_role",
        ),
    )
    op.create_table(
        "tenant_pricing_policies",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("minor_units", sa.SmallInteger(), nullable=False),
        sa.Column("rounding_mode", sa.String(16), nullable=False),
        sa.Column("tax_rate", sa.Numeric(7, 6), nullable=False),
        sa.Column("max_price_age_seconds", sa.Integer(), nullable=False),
        sa.Column("max_stock_age_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("tenant_id", name="pk_tenant_pricing_policies"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_tenant_pricing_policies_tenant_id_tenants"
        ),
        sa.CheckConstraint("version >= 1", name="ck_tenant_pricing_policies_version"),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_tenant_pricing_policies_currency"),
        sa.CheckConstraint(
            "minor_units BETWEEN 0 AND 4", name="ck_tenant_pricing_policies_minor_units"
        ),
        sa.CheckConstraint(
            "rounding_mode IN ('half_up', 'half_even')",
            name="ck_tenant_pricing_policies_rounding_mode",
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate < 1", name="ck_tenant_pricing_policies_tax_rate"
        ),
        sa.CheckConstraint(
            "max_price_age_seconds > 0 AND max_stock_age_seconds > 0",
            name="ck_tenant_pricing_policies_ages",
        ),
    )
    _protect("memberships")
    _protect("tenant_pricing_policies")


def downgrade() -> None:
    op.drop_table("tenant_pricing_policies")
    op.drop_table("memberships")
