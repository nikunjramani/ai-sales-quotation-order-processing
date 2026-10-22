"""Table metadata. Tenant-owned tables carry tenant_id and are protected by forced RLS."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
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


ENQUIRY_STATUS_CHECK = (
    "status IN ('received', 'ready_for_extraction', 'needs_review', "
    "'ready_for_quotation', 'needs_clarification')"
)
ROLE_CHECK = "role IN ('administrator', 'sales_operator', 'approver', 'viewer', 'intake_service')"


class ApiKey(Base):
    """Service-account credential. Only a SHA-256 hash of the secret is stored."""

    __tablename__ = "api_keys"
    __table_args__ = (CheckConstraint(ROLE_CHECK, name="ck_api_keys_role"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(32))
    secret_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InboxEvent(Base):
    """Durable receipt of one provider event; the unique key makes replays detectable."""

    __tablename__ = "inbox_events"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "channel",
            "connection_id",
            "provider_event_id",
            name="uq_inbox_events_provider_event",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_inbox_events_tenant_id_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    channel: Mapped[str] = mapped_column(String(32))
    connection_id: Mapped[str] = mapped_column(String(100))
    provider_event_id: Mapped[str] = mapped_column(String(200))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    envelope: Mapped[dict[str, object]] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[UUID] = mapped_column()


class Enquiry(Base):
    __tablename__ = "enquiries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "inbox_event_id"],
            ["inbox_events.tenant_id", "inbox_events.id"],
            name="fk_enquiries_inbox_event",
        ),
        UniqueConstraint("inbox_event_id", name="uq_enquiries_inbox_event_id"),
        UniqueConstraint("tenant_id", "id", name="uq_enquiries_tenant_id_id"),
        CheckConstraint(
            ENQUIRY_STATUS_CHECK,
            name="ck_enquiries_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    inbox_event_id: Mapped[UUID] = mapped_column()
    channel: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    customer_reference: Mapped[str | None] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[UUID] = mapped_column()
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "enquiry_id"],
            ["enquiries.tenant_id", "enquiries.id"],
            name="fk_attachments_enquiry",
        ),
        Index("ix_attachments_tenant_enquiry", "tenant_id", "enquiry_id"),
        CheckConstraint(
            "status IN ('quarantined', 'clean', 'rejected')", name="ck_attachments_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    enquiry_id: Mapped[UUID] = mapped_column()
    filename: Mapped[str] = mapped_column(String(255))
    declared_content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    detected_content_type: Mapped[str | None] = mapped_column(String(100))
    rejection_reason: Mapped[str | None] = mapped_column(String(50))
    storage_key: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    """Durable work item. Payload holds references only, never documents or secrets."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_claim", "status", "run_at"),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'dead')", name="ck_jobs_status"
        ),
        CheckConstraint("attempts >= 0 AND max_attempts >= 1", name="ck_jobs_attempts"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    kind: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    correlation_id: Mapped[UUID] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkflowRun(Base):
    """Maps one tenant's enquiry to a LangGraph thread (run ID = thread ID) and its outcome.

    Checkpoint tables have no tenant column, so they are only ever opened through this mapping.
    """

    __tablename__ = "workflow_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "enquiry_id"],
            ["enquiries.tenant_id", "enquiries.id"],
            name="fk_workflow_runs_enquiry",
        ),
        UniqueConstraint(
            "tenant_id", "enquiry_id", "graph_version", name="uq_workflow_runs_enquiry_version"
        ),
        CheckConstraint(
            "status IN ('running', 'ready_for_quotation', 'needs_clarification', 'needs_review')",
            name="ck_workflow_runs_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    enquiry_id: Mapped[UUID] = mapped_column()
    graph_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(32))
    outcome: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
