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
        CheckConstraint(
            "quote_validity_days >= 1", name="ck_tenant_pricing_policies_quote_validity"
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
    # Days an issued quotation can be accepted, counted from delivery (M6; default 7).
    quote_validity_days: Mapped[int] = mapped_column(Integer, server_default=text("7"))
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


WORKFLOW_RUN_STATUS_CHECK = (
    "status IN ('running', 'ready_for_quotation', 'needs_clarification', 'needs_review', "
    "'approved', 'rejected', 'accepted', 'declined', 'expired', 'withdrawn')"
)


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
        CheckConstraint(WORKFLOW_RUN_STATUS_CHECK, name="ck_workflow_runs_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    enquiry_id: Mapped[UUID] = mapped_column()
    graph_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(32))
    outcome: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    """Portal session for a person. Not tenant-owned: one person may belong to many tenants.

    Only the SHA-256 hash of the token is stored; RLS shows the API role only the row whose
    hash it presents (like API keys).
    """

    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    subject: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


QUOTATION_STATUS_CHECK = (
    "status IN ('pricing_failed', 'pending_approval', 'revision_requested', "
    "'revision_submitted', 'approved', 'rejected', 'accepted', 'declined', 'expired', "
    "'withdrawn')"
)


class Quotation(Base):
    """One quotation per enquiry; its versions are immutable snapshots."""

    __tablename__ = "quotations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "enquiry_id"],
            ["enquiries.tenant_id", "enquiries.id"],
            name="fk_quotations_enquiry",
        ),
        UniqueConstraint("tenant_id", "enquiry_id", name="uq_quotations_tenant_enquiry"),
        UniqueConstraint("tenant_id", "id", name="uq_quotations_tenant_id_id"),
        CheckConstraint(QUOTATION_STATUS_CHECK, name="ck_quotations_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    enquiry_id: Mapped[UUID] = mapped_column()
    status: Mapped[str] = mapped_column(String(32))
    current_version: Mapped[int | None] = mapped_column(Integer)
    pricing_issues: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuotationVersion(Base):
    """Immutable: no role may UPDATE or DELETE (grants and a trigger enforce it)."""

    __tablename__ = "quotation_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "quotation_id"],
            ["quotations.tenant_id", "quotations.id"],
            name="fk_quotation_versions_quotation",
        ),
        UniqueConstraint(
            "tenant_id", "quotation_id", "version", name="uq_quotation_versions_number"
        ),
        UniqueConstraint("tenant_id", "id", name="uq_quotation_versions_tenant_id_id"),
        UniqueConstraint("tenant_id", "command_id", name="uq_quotation_versions_command"),
        CheckConstraint("version >= 1", name="ck_quotation_versions_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    quotation_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, object]] = mapped_column(JSONB)
    content_sha256: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    created_by: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(String(1000))
    command_id: Mapped[UUID | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApprovalTask(Base):
    __tablename__ = "approval_tasks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "version_id"],
            ["quotation_versions.tenant_id", "quotation_versions.id"],
            name="fk_approval_tasks_version",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "quotation_id"],
            ["quotations.tenant_id", "quotations.id"],
            name="fk_approval_tasks_quotation",
        ),
        UniqueConstraint("tenant_id", "version_id", name="uq_approval_tasks_version"),
        UniqueConstraint("tenant_id", "id", name="uq_approval_tasks_tenant_id_id"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'revision_requested')",
            name="ck_approval_tasks_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    quotation_id: Mapped[UUID] = mapped_column()
    version_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    content_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalDecision(Base):
    """Audit record of one decision. Immutable; at most one per task."""

    __tablename__ = "approval_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "task_id"],
            ["approval_tasks.tenant_id", "approval_tasks.id"],
            name="fk_approval_decisions_task",
        ),
        UniqueConstraint("tenant_id", "task_id", name="uq_approval_decisions_task"),
        UniqueConstraint("tenant_id", "command_id", name="uq_approval_decisions_command"),
        CheckConstraint(
            "action IN ('approve', 'reject', 'request_revision')",
            name="ck_approval_decisions_action",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    task_id: Mapped[UUID] = mapped_column()
    command_id: Mapped[UUID] = mapped_column()
    quotation_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    content_sha256: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(32))
    actor_subject: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(String(1000))
    transport: Mapped[str] = mapped_column(String(32))
    evidence_ref: Mapped[str | None] = mapped_column(String(300))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChannelEnrollment(Base):
    """A one-time code proving that the signed-in manager controls a channel account."""

    __tablename__ = "channel_enrollments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code_sha256", name="uq_channel_enrollments_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    subject: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(32))
    code_sha256: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChannelBindingRow(Base):
    """An internal manager's enrolled account on one approval channel connection."""

    __tablename__ = "channel_bindings"
    __table_args__ = (
        Index(
            "uq_channel_bindings_active_account",
            "tenant_id",
            "channel",
            "connection_id",
            "external_user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        UniqueConstraint("tenant_id", "id", name="uq_channel_bindings_tenant_id_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    subject: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(32))
    connection_id: Mapped[str] = mapped_column(String(100))
    external_user_id: Mapped[str] = mapped_column(String(200))
    enrollment_id: Mapped[UUID] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalActionRef(Base):
    """Opaque single-use action reference sent to one bound account for one task."""

    __tablename__ = "approval_action_refs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "task_id"],
            ["approval_tasks.tenant_id", "approval_tasks.id"],
            name="fk_approval_action_refs_task",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "binding_id"],
            ["channel_bindings.tenant_id", "channel_bindings.id"],
            name="fk_approval_action_refs_binding",
        ),
        UniqueConstraint("tenant_id", "task_id", "binding_id", name="uq_approval_action_refs_task"),
        UniqueConstraint("token_sha256", name="uq_approval_action_refs_token"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    task_id: Mapped[UUID] = mapped_column()
    binding_id: Mapped[UUID] = mapped_column()
    token_sha256: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


DELIVERY_STATUS_CHECK = "status IN ('pending', 'sending', 'available', 'sent', 'failed', 'unknown')"


class QuotationDocument(Base):
    """Rendered PDF of one approved version. Immutable (grants and a trigger enforce it)."""

    __tablename__ = "quotation_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            [
                "quotation_versions.tenant_id",
                "quotation_versions.quotation_id",
                "quotation_versions.version",
            ],
            name="fk_quotation_documents_version",
        ),
        UniqueConstraint(
            "tenant_id", "quotation_id", "version", "kind", name="uq_quotation_documents_version"
        ),
        UniqueConstraint("tenant_id", "id", name="uq_quotation_documents_tenant_id_id"),
        CheckConstraint("kind IN ('approved')", name="ck_quotation_documents_kind"),
        CheckConstraint("size_bytes > 0", name="ck_quotation_documents_size"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    quotation_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    content_sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    renderer: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QuotationDelivery(Base):
    """Outbox row: one approved version to one recipient on one channel, with its outcome."""

    __tablename__ = "quotation_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            [
                "quotation_versions.tenant_id",
                "quotation_versions.quotation_id",
                "quotation_versions.version",
            ],
            name="fk_quotation_deliveries_version",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            ["quotation_documents.tenant_id", "quotation_documents.id"],
            name="fk_quotation_deliveries_document",
        ),
        UniqueConstraint(
            "tenant_id",
            "quotation_id",
            "version",
            "channel",
            "recipient",
            name="uq_quotation_deliveries_target",
        ),
        CheckConstraint(DELIVERY_STATUS_CHECK, name="ck_quotation_deliveries_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    quotation_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(32))
    recipient: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16))
    document_id: Mapped[UUID | None] = mapped_column()
    provider_reference: Mapped[str | None] = mapped_column(String(200))
    last_error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


RESPONSE_OUTCOME_CHECK = (
    "outcome IN ('accepted', 'declined', 'refused_changed', 'withdrawn', 'expired')"
)


class QuotationResponse(Base):
    """An answer to an issued version: customer accept/decline, staff withdrawal or expiry.

    Append-only (grants and a trigger). At most one closing outcome per quotation.
    """

    __tablename__ = "quotation_responses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            [
                "quotation_versions.tenant_id",
                "quotation_versions.quotation_id",
                "quotation_versions.version",
            ],
            name="fk_quotation_responses_version",
        ),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_quotation_responses_key"),
        CheckConstraint(RESPONSE_OUTCOME_CHECK, name="ck_quotation_responses_outcome"),
        Index(
            "uq_quotation_responses_closing",
            "tenant_id",
            "quotation_id",
            unique=True,
            postgresql_where=text("outcome <> 'refused_changed'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    quotation_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    content_sha256: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16))
    actor: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(String(1000))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    fingerprint: Mapped[str] = mapped_column(String(64))
    differences: Mapped[list[str]] = mapped_column(JSONB)
    revised_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
