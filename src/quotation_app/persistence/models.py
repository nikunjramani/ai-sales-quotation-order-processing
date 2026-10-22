"""Table metadata. Tenant-owned tables carry tenant_id and are protected by forced RLS."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        }
    )


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    """One role held by an authenticated subject within one tenant."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "subject", "role", name="uq_memberships_tenant_subject_role"),
        CheckConstraint(
            "role IN ('administrator', 'sales_operator', 'approver', 'viewer')",
            name="ck_memberships_role",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    subject: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TenantPricingPolicy(Base):
    """Current pricing policy per tenant; version increases whenever values change."""

    __tablename__ = "tenant_pricing_policies"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_tenant_pricing_policies_version"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_tenant_pricing_policies_currency"),
        CheckConstraint(
            "minor_units BETWEEN 0 AND 4", name="ck_tenant_pricing_policies_minor_units"
        ),
        CheckConstraint(
            "rounding_mode IN ('half_up', 'half_even')",
            name="ck_tenant_pricing_policies_rounding_mode",
        ),
        CheckConstraint(
            "tax_rate >= 0 AND tax_rate < 1", name="ck_tenant_pricing_policies_tax_rate"
        ),
        CheckConstraint(
            "max_price_age_seconds > 0 AND max_stock_age_seconds > 0",
            name="ck_tenant_pricing_policies_ages",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    minor_units: Mapped[int] = mapped_column(SmallInteger)
    rounding_mode: Mapped[str] = mapped_column(String(16))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    max_price_age_seconds: Mapped[int] = mapped_column(Integer)
    max_stock_age_seconds: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
