"""Unit-test fakes for M4: one in-memory "database" implementing every quotation/approval port.

It mirrors the SQL rules that matter for behaviour (one task per version, one decision per
task, unique command IDs, optimistic revision checks, single-use action references) so the
services, graph and routes can be tested without PostgreSQL. tests/integration proves the
real SQL implementations follow the same rules.
"""

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from quotation_app.adapters.erp.simulated import SimulatedErp
from quotation_app.application.approvals import ApprovalService
from quotation_app.application.channel_actions import ChannelActionService
from quotation_app.application.notifications import ApprovalNotificationHandler
from quotation_app.application.pricing import QuotationPricingService
from quotation_app.application.quotations import QuotationService
from quotation_app.application.tenancy import TenantContextResolver
from quotation_app.domain.jobs import JobKind
from quotation_app.domain.pricing import RequestedLine
from quotation_app.domain.quotations import (
    QUOTATION_STATUS_AFTER,
    REVISABLE,
    TASK_STATUS_AFTER,
    ApprovalAction,
    DecisionCommand,
    QuotationStatus,
    RecordedDecision,
    ReviewPacket,
    RevisionConflict,
    TaskStatus,
    quotation_number,
)
from quotation_app.domain.tenancy import Role, TenantContext
from quotation_app.ports.approvals import TaskState
from quotation_app.ports.channels import ActionReference, ChannelBinding
from quotation_app.ports.identity import SessionRecord, VerifiedIdentity
from quotation_app.ports.jobs import ClaimedJob
from quotation_app.ports.quotations import (
    QuotationDetail,
    QuotationSummary,
    TaskView,
    VersionView,
)
from quotation_app.workflows.quotation import (
    QuotationJobHandler,
    QuotationWorkflowDeps,
    build_quotation_graph,
)


@dataclass
class QuotationRow:
    quotation_id: UUID
    tenant_id: UUID
    enquiry_id: UUID
    status: QuotationStatus
    current_version: int | None
    pricing_issues: list[Mapping[str, object]]
    updated_at: datetime


@dataclass
class VersionRow:
    view: VersionView
    tenant_id: UUID
    quotation_id: UUID
    command_id: UUID | None


@dataclass
class TaskRow:
    task_id: UUID
    tenant_id: UUID
    quotation_id: UUID
    version: int
    content_sha256: str
    status: TaskStatus
    created_at: datetime
    decided_at: datetime | None = None


@dataclass
class ReferenceRow:
    reference_id: UUID
    tenant_id: UUID
    task_id: UUID
    binding_id: UUID
    token_sha256: str
    expires_at: datetime
    sent_at: datetime | None = None
    consumed_at: datetime | None = None


@dataclass
class EnrollmentRow:
    enrollment_id: UUID
    tenant_id: UUID
    subject: str
    channel: str
    code_sha256: str
    expires_at: datetime
    consumed_at: datetime | None = None


@dataclass
class Job:
    tenant_id: UUID
    kind: JobKind
    payload: dict[str, str]


class _RunLock:
    def __init__(self, db: "MemoryQuotations", run_id: UUID) -> None:
        self._db, self._run_id, self._held = db, run_id, False

    def __enter__(self) -> bool:
        self._held = self._run_id not in self._db.locked_runs
        if self._held:
            self._db.locked_runs.add(self._run_id)
        return self._held

    def __exit__(self, *exc: object) -> None:
        if self._held:
            self._db.locked_runs.discard(self._run_id)


class _DecisionUnit:
    def __init__(self, db: "MemoryQuotations", tenant_id: UUID, task: TaskState) -> None:
        self._db, self._tenant_id, self._task = db, tenant_id, task

    @property
    def task(self) -> TaskState:
        return self._task

    def record(
        self, decision: RecordedDecision, command: DecisionCommand, consume_reference: UUID | None
    ) -> None:
        db = self._db
        db.decisions[decision.decision_id] = (self._tenant_id, decision)
        row = db.tasks[decision.task_id]
        row.status = TASK_STATUS_AFTER[decision.action]
        row.decided_at = decision.decided_at
        quotation = db.quotations[decision.quotation_id]
        quotation.status = QUOTATION_STATUS_AFTER[decision.action]
        if consume_reference is not None:
            db.references[consume_reference].consumed_at = db.clock()
        db.jobs.append(
            Job(
                self._tenant_id,
                JobKind.RESUME_QUOTATION,
                {
                    "enquiry_id": str(quotation.enquiry_id),
                    "waiting_for": "decision",
                    "task_id": str(decision.task_id),
                    "decision_id": str(decision.decision_id),
                },
            )
        )


@dataclass
class MemoryQuotations:
    clock: Callable[[], datetime]
    roles: dict[tuple[UUID, str], frozenset[Role]] = field(default_factory=dict)
    tenant_names: dict[UUID, str] = field(default_factory=dict)
    extraction: dict[tuple[UUID, UUID], list[RequestedLine]] = field(default_factory=dict)
    customer_refs: dict[UUID, str | None] = field(default_factory=dict)
    runs: dict[tuple[UUID, UUID, str], UUID] = field(default_factory=dict)
    run_status: dict[UUID, str] = field(default_factory=dict)
    locked_runs: set[UUID] = field(default_factory=set)
    quotations: dict[UUID, QuotationRow] = field(default_factory=dict)
    versions: list[VersionRow] = field(default_factory=list)
    tasks: dict[UUID, TaskRow] = field(default_factory=dict)
    decisions: dict[UUID, tuple[UUID, RecordedDecision]] = field(default_factory=dict)
    jobs: list[Job] = field(default_factory=list)
    bindings: dict[UUID, ChannelBinding] = field(default_factory=dict)
    enrollments: dict[UUID, EnrollmentRow] = field(default_factory=dict)
    binding_enrollment: dict[UUID, UUID] = field(default_factory=dict)
    references: dict[UUID, ReferenceRow] = field(default_factory=dict)
    sessions: dict[str, SessionRecord] = field(default_factory=dict)
    # Name of a method -> exception raised on its next call (failure injection).
    fail_next: dict[str, Exception] = field(default_factory=dict)

    def _maybe_fail(self, name: str) -> None:
        error = self.fail_next.pop(name, None)
        if error is not None:
            raise error

    # --- test helpers -------------------------------------------------------------------
    def add_member(self, tenant_id: UUID, subject: str, *roles: Role) -> None:
        self.roles[(tenant_id, subject)] = frozenset(roles) | self.roles.get(
            (tenant_id, subject), frozenset()
        )

    def take_jobs(self, kind: JobKind | None = None) -> list[Job]:
        taken = [job for job in self.jobs if kind is None or job.kind is kind]
        self.jobs = [job for job in self.jobs if job not in taken]
        return taken

    def _versions(self, tenant_id: UUID, quotation_id: UUID) -> list[VersionRow]:
        return sorted(
            (
                row
                for row in self.versions
                if row.tenant_id == tenant_id and row.quotation_id == quotation_id
            ),
            key=lambda row: row.view.version,
        )

    def _quotation(self, tenant_id: UUID, quotation_id: UUID) -> QuotationRow | None:
        row = self.quotations.get(quotation_id)
        return row if row is not None and row.tenant_id == tenant_id else None

    def _add_version(
        self,
        tenant_id: UUID,
        quotation_id: UUID,
        version: int,
        content: Mapping[str, object],
        sha: str,
        created_by: str,
        reason: str | None,
        command_id: UUID | None,
    ) -> None:
        if any(
            row.tenant_id == tenant_id and row.command_id == command_id and command_id
            for row in self.versions
        ):
            raise RevisionConflict("duplicate command")
        self.versions.append(
            VersionRow(
                VersionView(uuid4(), version, dict(content), sha, created_by, reason, self.clock()),
                tenant_id,
                quotation_id,
                command_id,
            )
        )

    # --- MembershipReader -----------------------------------------------------------------
    def roles_for(self, tenant_id: UUID, subject: str) -> frozenset[Role]:
        return self.roles.get((tenant_id, subject), frozenset())

    # --- QuotationWorkflowStore -----------------------------------------------------------
    def start_run(self, tenant_id: UUID, enquiry_id: UUID, graph_version: str) -> UUID:
        return self.runs.setdefault((tenant_id, enquiry_id, graph_version), uuid4())

    def lock_run(self, run_id: UUID) -> _RunLock:
        return _RunLock(self, run_id)

    def extraction_lines(self, tenant_id: UUID, enquiry_id: UUID) -> list[RequestedLine] | None:
        return self.extraction.get((tenant_id, enquiry_id))

    def create_quotation(
        self,
        tenant_id: UUID,
        enquiry_id: UUID,
        content: Mapping[str, object] | None,
        content_sha256: str | None,
        pricing_issues: Sequence[Mapping[str, object]] | None,
        created_by: str,
    ) -> tuple[UUID, int | None]:
        self._maybe_fail("create_quotation")
        for row in self.quotations.values():
            if row.tenant_id == tenant_id and row.enquiry_id == enquiry_id:
                return row.quotation_id, row.current_version
        quotation_id = uuid4()
        priced = content is not None and content_sha256 is not None
        self.quotations[quotation_id] = QuotationRow(
            quotation_id,
            tenant_id,
            enquiry_id,
            QuotationStatus.PENDING_APPROVAL if priced else QuotationStatus.PRICING_FAILED,
            1 if priced else None,
            list(pricing_issues or []),
            self.clock(),
        )
        if content is not None and content_sha256 is not None:
            self._add_version(
                tenant_id, quotation_id, 1, content, content_sha256, created_by, None, None
            )
        return quotation_id, 1 if priced else None

    def current_version(self, tenant_id: UUID, quotation_id: UUID) -> int | None:
        row = self._quotation(tenant_id, quotation_id)
        return None if row is None else row.current_version

    def request_approval(self, tenant_id: UUID, quotation_id: UUID, version: int) -> UUID:
        self._maybe_fail("request_approval")
        stored = next(
            row for row in self._versions(tenant_id, quotation_id) if row.view.version == version
        )
        for task in self.tasks.values():
            if task.tenant_id == tenant_id and task.quotation_id == quotation_id:
                if task.version == version:
                    return task.task_id
        task_id = uuid4()
        self.tasks[task_id] = TaskRow(
            task_id,
            tenant_id,
            quotation_id,
            version,
            stored.view.content_sha256,
            TaskStatus.PENDING,
            self.clock(),
        )
        quotation = self.quotations[quotation_id]
        quotation.status = QuotationStatus.PENDING_APPROVAL
        self.jobs.append(
            Job(
                tenant_id,
                JobKind.NOTIFY_APPROVERS,
                {"task_id": str(task_id), "enquiry_id": str(quotation.enquiry_id)},
            )
        )
        return task_id

    def decision(self, tenant_id: UUID, decision_id: UUID) -> RecordedDecision | None:
        found = self.decisions.get(decision_id)
        return found[1] if found is not None and found[0] == tenant_id else None

    def finish(self, tenant_id: UUID, run_id: UUID, status: str) -> None:
        self.run_status[run_id] = status

    # --- ApprovalStore --------------------------------------------------------------------
    def find_by_command(self, tenant_id: UUID, command_id: UUID) -> RecordedDecision | None:
        return next(
            (
                decision
                for tenant, decision in self.decisions.values()
                if tenant == tenant_id and decision.command_id == command_id
            ),
            None,
        )

    @contextmanager
    def locked_task(self, tenant_id: UUID, task_id: UUID) -> Iterator[_DecisionUnit | None]:
        task = self.tasks.get(task_id)
        if task is None or task.tenant_id != tenant_id:
            yield None
            return
        quotation = self.quotations[task.quotation_id]
        version = next(
            row
            for row in self._versions(tenant_id, task.quotation_id)
            if row.view.version == task.version
        )
        decision = next((d for tenant, d in self.decisions.values() if d.task_id == task_id), None)
        yield _DecisionUnit(
            self,
            tenant_id,
            TaskState(
                task.task_id,
                task.quotation_id,
                task.version,
                task.content_sha256,
                task.status,
                quotation.current_version,
                version.view.created_by,
                decision,
            ),
        )

    # --- QuotationReader / QuotationRevisionStore -----------------------------------------
    def _summary(self, row: QuotationRow) -> QuotationSummary:
        current = next(
            (
                version
                for version in self._versions(row.tenant_id, row.quotation_id)
                if version.view.version == row.current_version
            ),
            None,
        )
        return QuotationSummary(
            row.quotation_id,
            row.enquiry_id,
            quotation_number(row.quotation_id),
            row.status,
            row.current_version,
            self.customer_refs.get(row.enquiry_id),
            None if current is None else str(current.view.content["currency"]),
            None if current is None else str(current.view.content["total"]),
            row.updated_at,
        )

    def find_revision(self, tenant_id: UUID, command_id: UUID) -> tuple[UUID, int] | None:
        return next(
            (
                (row.quotation_id, row.view.version)
                for row in self.versions
                if row.tenant_id == tenant_id and row.command_id == command_id
            ),
            None,
        )

    def add_revision(
        self,
        tenant_id: UUID,
        quotation_id: UUID,
        base_version: int | None,
        content: Mapping[str, object],
        content_sha256: str,
        created_by: str,
        reason: str | None,
        command_id: UUID,
    ) -> int:
        row = self._quotation(tenant_id, quotation_id)
        if row is None or row.current_version != base_version or row.status not in REVISABLE:
            raise RevisionConflict("changed")
        version = (base_version or 0) + 1
        self._add_version(
            tenant_id, quotation_id, version, content, content_sha256, created_by, reason,
            command_id,
        )  # fmt: skip
        row.current_version = version
        row.status = QuotationStatus.REVISION_SUBMITTED
        self.jobs.append(
            Job(
                tenant_id,
                JobKind.RESUME_QUOTATION,
                {
                    "enquiry_id": str(row.enquiry_id),
                    "waiting_for": "revision",
                    "version": str(version),
                },
            )
        )
        return version

    # --- NotificationStore ----------------------------------------------------------------
    def review_packet(self, tenant_id: UUID, task_id: UUID) -> ReviewPacket | None:
        task = self.tasks.get(task_id)
        if task is None or task.tenant_id != tenant_id or task.status is not TaskStatus.PENDING:
            return None
        version = next(
            row
            for row in self._versions(tenant_id, task.quotation_id)
            if row.view.version == task.version
        )
        quotation = self.quotations[task.quotation_id]
        return ReviewPacket(
            tenant_id,
            self.tenant_names.get(tenant_id, "Demo"),
            task_id,
            task.quotation_id,
            task.version,
            task.content_sha256,
            self.customer_refs.get(quotation.enquiry_id),
            version.view.content,
        )

    def approver_bindings(self, tenant_id: UUID) -> list[ChannelBinding]:
        return [
            binding
            for binding in self.bindings.values()
            if binding.tenant_id == tenant_id
            and binding.active
            and Role.APPROVER in self.roles.get((tenant_id, binding.subject), frozenset())
        ]

    def prepare_reference(
        self,
        tenant_id: UUID,
        task_id: UUID,
        binding_id: UUID,
        token_sha256: str,
        expires_at: datetime,
    ) -> UUID | None:
        self._maybe_fail("prepare_reference")
        for row in self.references.values():
            if (row.tenant_id, row.task_id, row.binding_id) == (tenant_id, task_id, binding_id):
                if row.sent_at is not None:
                    return None
                row.token_sha256, row.expires_at = token_sha256, expires_at
                return row.reference_id
        reference_id = uuid4()
        self.references[reference_id] = ReferenceRow(
            reference_id, tenant_id, task_id, binding_id, token_sha256, expires_at
        )
        return reference_id

    def mark_sent(self, tenant_id: UUID, reference_id: UUID) -> None:
        self.references[reference_id].sent_at = self.clock()

    # --- ChannelStore ---------------------------------------------------------------------
    def create_enrollment(
        self, tenant_id: UUID, subject: str, channel: str, code_sha256: str, expires_at: datetime
    ) -> None:
        enrollment_id = uuid4()
        self.enrollments[enrollment_id] = EnrollmentRow(
            enrollment_id, tenant_id, subject, channel, code_sha256, expires_at
        )

    def enroll(
        self,
        tenant_id: UUID,
        channel: str,
        connection_id: str,
        external_user_id: str,
        code_sha256: str,
        now: datetime,
    ) -> ChannelBinding | None:
        row = next(
            (
                item
                for item in self.enrollments.values()
                if item.tenant_id == tenant_id and item.code_sha256 == code_sha256
            ),
            None,
        )
        if row is None or row.channel != channel:
            return None

        def same(binding: ChannelBinding) -> bool:
            return (binding.tenant_id, binding.channel, binding.connection_id,
                    binding.external_user_id) == (tenant_id, channel, connection_id,
                                                  external_user_id)  # fmt: skip

        if row.consumed_at is not None:
            return next(
                (
                    binding
                    for binding_id, binding in self.bindings.items()
                    if same(binding) and self.binding_enrollment[binding_id] == row.enrollment_id
                ),
                None,
            )
        if row.expires_at <= now or any(
            same(binding) and binding.active for binding in self.bindings.values()
        ):
            return None
        binding = ChannelBinding(
            uuid4(), tenant_id, row.subject, channel, connection_id, external_user_id, now, None
        )
        self.bindings[binding.binding_id] = binding
        self.binding_enrollment[binding.binding_id] = row.enrollment_id
        row.consumed_at = now
        return binding

    def find_reference(
        self, tenant_id: UUID, token_sha256: str
    ) -> tuple[ActionReference, ChannelBinding] | None:
        for row in self.references.values():
            if row.tenant_id == tenant_id and row.token_sha256 == token_sha256 and row.sent_at:
                task = self.tasks[row.task_id]
                return (
                    ActionReference(
                        row.reference_id,
                        row.task_id,
                        row.binding_id,
                        task.content_sha256,
                        row.expires_at,
                        row.consumed_at,
                    ),
                    self.bindings[row.binding_id],
                )
        return None

    def bindings_for(self, tenant_id: UUID, subject: str | None) -> list[ChannelBinding]:
        return [
            binding
            for binding in self.bindings.values()
            if binding.tenant_id == tenant_id and (subject is None or binding.subject == subject)
        ]

    def revoke(self, tenant_id: UUID, binding_id: UUID, subject: str | None) -> bool:
        binding = self.bindings.get(binding_id)
        if (
            binding is None
            or binding.tenant_id != tenant_id
            or not binding.active
            or (subject is not None and binding.subject != subject)
        ):
            return False
        self.bindings[binding_id] = replace(binding, revoked_at=self.clock())
        return True

    # --- SessionStore ---------------------------------------------------------------------
    def create(
        self,
        session_id: UUID,
        token_sha256: str,
        identity: VerifiedIdentity,
        expires_at: datetime,
    ) -> None:
        self.sessions[token_sha256] = SessionRecord(
            session_id, identity.subject, identity.provider, expires_at, False
        )

    def find(self, token_sha256: str) -> SessionRecord | None:
        return self.sessions.get(token_sha256)

    def revoke_session(self, token_sha256: str) -> None:
        record = self.sessions.get(token_sha256)
        if record is not None:
            self.sessions[token_sha256] = replace(record, revoked=True)

    # --- QuotationReader (last: `list` would shadow the builtin in later annotations) --
    def list(
        self, tenant_id: UUID, statuses: frozenset[QuotationStatus] | None, limit: int
    ) -> list[QuotationSummary]:
        rows = [
            row
            for row in self.quotations.values()
            if row.tenant_id == tenant_id and (statuses is None or row.status in statuses)
        ]
        return [self._summary(row) for row in rows][:limit]

    def get(self, tenant_id: UUID, quotation_id: UUID) -> QuotationDetail | None:
        row = self._quotation(tenant_id, quotation_id)
        if row is None:
            return None
        tasks = sorted(
            (task for task in self.tasks.values() if task.quotation_id == quotation_id),
            key=lambda task: task.version,
        )
        return QuotationDetail(
            summary=self._summary(row),
            enquiry_text="Please quote 2 x IND-FAN-450",
            pricing_issues=list(row.pricing_issues),
            versions=tuple(version.view for version in self._versions(tenant_id, quotation_id)),
            tasks=tuple(
                TaskView(
                    task.task_id,
                    task.version,
                    task.content_sha256,
                    task.status,
                    task.created_at,
                    task.decided_at,
                )
                for task in tasks
            ),
            decisions=tuple(
                decision
                for tenant, decision in self.decisions.values()
                if decision.quotation_id == quotation_id
            ),
        )


class MemorySessions:
    """SessionStore view of MemoryQuotations (its revoke name is taken by bindings)."""

    def __init__(self, db: MemoryQuotations) -> None:
        self._db = db

    def create(
        self, session_id: UUID, token_sha256: str, identity: VerifiedIdentity, expires: datetime
    ) -> None:
        self._db.create(session_id, token_sha256, identity, expires)

    def find(self, token_sha256: str) -> SessionRecord | None:
        return self._db.find(token_sha256)

    def revoke(self, token_sha256: str) -> None:
        self._db.revoke_session(token_sha256)


class MemoryDirectory:
    """MembershipDirectory over MemoryQuotations.roles."""

    def __init__(self, db: MemoryQuotations) -> None:
        self._db = db

    def tenants_for(self, subject: str) -> list[Any]:
        from quotation_app.ports.tenancy import TenantMembership

        return [
            TenantMembership(tenant, self._db.tenant_names.get(tenant, "Demo"), roles)
            for (tenant, member), roles in self._db.roles.items()
            if member == subject
        ]


@pytest.fixture
def quotation_db(now: datetime, industrial_tenant: UUID, office_tenant: UUID) -> MemoryQuotations:
    db = MemoryQuotations(clock=lambda: now)
    db.tenant_names = {industrial_tenant: "Demo Industrial", office_tenant: "Demo Office"}
    db.add_member(industrial_tenant, "manager@industrial.example", Role.APPROVER)
    db.add_member(industrial_tenant, "sales@industrial.example", Role.SALES_OPERATOR)
    db.add_member(industrial_tenant, "viewer@industrial.example", Role.VIEWER)
    db.add_member(office_tenant, "sales@office.example", Role.SALES_OPERATOR)
    return db


class RecordingNotifier:
    """ApprovalNotifier fake: keeps sent messages; `fail` makes the next send raise."""

    channel = "simulated"

    def __init__(self) -> None:
        self.sent: list[tuple[ChannelBinding, ReviewPacket, str]] = []
        self.fail = False

    def send_review(
        self, binding: ChannelBinding, packet: ReviewPacket, reference: str, expires_at: datetime
    ) -> None:
        if self.fail:
            self.fail = False
            raise OSError("provider unavailable")
        self.sent.append((binding, packet, reference))


@dataclass
class QuotationHarness:
    """The real M4 services, graph and job handlers over MemoryQuotations."""

    db: MemoryQuotations
    erp: SimulatedErp
    pricing: QuotationPricingService
    checkpointer: InMemorySaver
    notifier: RecordingNotifier
    approvals: ApprovalService
    quotations: QuotationService
    channels: ChannelActionService
    tenant_id: UUID
    clock: Callable[[], datetime]

    def handler(self) -> QuotationJobHandler:
        """A fresh graph on the same checkpoints, as after a worker restart."""
        graph = build_quotation_graph(
            QuotationWorkflowDeps(self.db, self.pricing), self.checkpointer
        )
        return QuotationJobHandler(graph, self.db)

    def notifications(self) -> ApprovalNotificationHandler:
        return ApprovalNotificationHandler(self.db, {"simulated": self.notifier}, clock=self.clock)

    def enquiry(self, *lines: tuple[str, str, str], tenant_id: UUID | None = None) -> UUID:
        enquiry_id = uuid4()
        tenant = tenant_id or self.tenant_id
        self.db.extraction[(tenant, enquiry_id)] = [
            RequestedLine(sku, Decimal(quantity), unit) for sku, quantity, unit in lines
        ]
        self.db.jobs.append(Job(tenant, JobKind.DRAFT_QUOTATION, {"enquiry_id": str(enquiry_id)}))
        return enquiry_id

    def run_jobs(self) -> int:
        """Run queued jobs (and the jobs they queue) until none are left."""
        handled = 0
        while self.db.jobs:
            job = self.db.jobs.pop(0)
            claimed = ClaimedJob(uuid4(), job.tenant_id, job.kind, job.payload, 1, 5, uuid4(),
                                 uuid4())  # fmt: skip
            if job.kind is JobKind.NOTIFY_APPROVERS:
                self.notifications()(claimed)
            else:
                self.handler()(claimed)
            handled += 1
        return handled

    def quotation(self, enquiry_id: UUID) -> QuotationRow:
        return next(row for row in self.db.quotations.values() if row.enquiry_id == enquiry_id)

    def pending_task(self, enquiry_id: UUID) -> TaskRow:
        quotation = self.quotation(enquiry_id)
        return next(
            task
            for task in self.db.tasks.values()
            if task.quotation_id == quotation.quotation_id and task.status is TaskStatus.PENDING
        )

    def command(
        self,
        task: TaskRow,
        action: ApprovalAction = ApprovalAction.APPROVE,
        reason: str | None = None,
        command_id: UUID | None = None,
        content_sha256: str | None = None,
    ) -> DecisionCommand:
        return DecisionCommand(
            command_id=command_id or uuid4(),
            tenant_id=task.tenant_id,
            task_id=task.task_id,
            content_sha256=content_sha256 or task.content_sha256,
            action=action,
            reason=reason,
            transport="portal",
            evidence_ref=None,
            received_at=self.clock(),
        )

    def context(self, subject: str, tenant_id: UUID | None = None) -> TenantContext:
        return TenantContextResolver(self.db).resolve(subject, tenant_id or self.tenant_id)


@pytest.fixture
def harness(
    quotation_db: MemoryQuotations,
    simulated_erp: SimulatedErp,
    policy_reader: Any,
    now: datetime,
    industrial_tenant: UUID,
) -> QuotationHarness:
    def clock() -> datetime:
        return now

    resolver = TenantContextResolver(quotation_db)
    pricing = QuotationPricingService(simulated_erp, policy_reader, clock=clock)
    approvals = ApprovalService(quotation_db, resolver, clock=clock)
    return QuotationHarness(
        db=quotation_db,
        erp=simulated_erp,
        pricing=pricing,
        checkpointer=InMemorySaver(),
        notifier=RecordingNotifier(),
        approvals=approvals,
        quotations=QuotationService(quotation_db, quotation_db, pricing),
        channels=ChannelActionService(quotation_db, approvals, clock=clock),
        tenant_id=industrial_tenant,
        clock=clock,
    )


@pytest.fixture
def memory_sessions(quotation_db: MemoryQuotations) -> MemorySessions:
    return MemorySessions(quotation_db)


@pytest.fixture
def memory_directory(quotation_db: MemoryQuotations) -> MemoryDirectory:
    return MemoryDirectory(quotation_db)
