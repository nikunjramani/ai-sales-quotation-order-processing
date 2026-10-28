"""Workflow runs (tenant-scoped) and the LangGraph PostgreSQL checkpointer (worker role)."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from uuid import UUID, uuid4

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from sqlalchemy import Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from quotation_app.domain.attachments import AttachmentStatus
from quotation_app.domain.intake import EnquiryStatus
from quotation_app.domain.jobs import JobKind
from quotation_app.domain.requirements import ExtractionOutcome
from quotation_app.persistence.jobs import queue_job
from quotation_app.persistence.models import Attachment, Enquiry, WorkflowRun
from quotation_app.persistence.tenancy import tenant_transaction
from quotation_app.ports.workflow import CleanAttachment, EnquiryContent

RUNNING = "running"


class SqlWorkflowStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enquiry_content(self, tenant_id: UUID, enquiry_id: UUID) -> EnquiryContent | None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            text = connection.execute(
                select(Enquiry.text).where(Enquiry.tenant_id == tenant_id, Enquiry.id == enquiry_id)
            ).scalar_one_or_none()
            if text is None:
                return None
            rows = connection.execute(
                select(
                    Attachment.id,
                    Attachment.filename,
                    Attachment.declared_content_type,
                    Attachment.storage_key,
                )
                .where(
                    Attachment.tenant_id == tenant_id,
                    Attachment.enquiry_id == enquiry_id,
                    Attachment.status == AttachmentStatus.CLEAN.value,
                )
                .order_by(Attachment.created_at, Attachment.id)
            ).all()
        return EnquiryContent(
            text,
            tuple(
                CleanAttachment(row.id, row.filename, row.declared_content_type, row.storage_key)
                for row in rows
            ),
        )

    def start_run(
        self, tenant_id: UUID, enquiry_id: UUID, graph_version: str, round: int = 1
    ) -> UUID:
        with tenant_transaction(self._engine, tenant_id) as connection:
            connection.execute(
                insert(WorkflowRun)
                .values(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    enquiry_id=enquiry_id,
                    graph_version=graph_version,
                    round=round,
                    status=RUNNING,
                )
                .on_conflict_do_nothing(
                    index_elements=["tenant_id", "enquiry_id", "graph_version", "round"]
                )
            )
            run_id: UUID = connection.execute(
                select(WorkflowRun.id).where(
                    WorkflowRun.tenant_id == tenant_id,
                    WorkflowRun.enquiry_id == enquiry_id,
                    WorkflowRun.graph_version == graph_version,
                    WorkflowRun.round == round,
                )
            ).scalar_one()
        return run_id

    def record_outcome(
        self,
        tenant_id: UUID,
        enquiry_id: UUID,
        run_id: UUID,
        outcome: ExtractionOutcome,
        details: Mapping[str, object],
    ) -> None:
        with tenant_transaction(self._engine, tenant_id) as connection:
            connection.execute(
                update(WorkflowRun)
                .where(WorkflowRun.tenant_id == tenant_id, WorkflowRun.id == run_id)
                .values(status=outcome.value, outcome=dict(details), updated_at=func.now())
            )
            moved = connection.execute(
                update(Enquiry)
                .where(
                    Enquiry.tenant_id == tenant_id,
                    Enquiry.id == enquiry_id,
                    Enquiry.status == EnquiryStatus.READY_FOR_EXTRACTION.value,
                )
                .values(status=EnquiryStatus(outcome.value).value, updated_at=func.now())
                .returning(Enquiry.correlation_id)
            ).one_or_none()
            # Only the first recording moves the enquiry on, so drafting is queued once (M4).
            if moved is not None and outcome is ExtractionOutcome.READY_FOR_QUOTATION:
                queue_job(
                    connection,
                    tenant_id,
                    JobKind.DRAFT_QUOTATION,
                    {"enquiry_id": str(enquiry_id)},
                    moved.correlation_id,
                )


def psycopg_url(sqlalchemy_url: str) -> str:
    """Convert postgresql+psycopg://... to the libpq form psycopg expects."""
    return (
        make_url(sqlalchemy_url).set(drivername="postgresql").render_as_string(hide_password=False)
    )


@contextmanager
def open_checkpointer(worker_url: str) -> Iterator[PostgresSaver]:
    """A dedicated worker-role connection for LangGraph checkpoints (autocommit, as required).

    The schema already exists (migration 0004), so setup() is never called at runtime.
    """
    connection: Connection[DictRow]
    with Connection.connect(
        psycopg_url(worker_url),
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
        connect_timeout=3,
    ) as connection:
        yield PostgresSaver(connection)
