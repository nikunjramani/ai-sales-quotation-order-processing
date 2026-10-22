"""Business-record access for the enquiry workflow (worker role, always tenant-scoped).

Workflow runs map a tenant's enquiry to a LangGraph thread. Checkpoints are only ever opened
through this mapping, so a thread ID from one tenant is never resumed for another.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from quotation_app.domain.requirements import ExtractionOutcome


@dataclass(frozen=True)
class CleanAttachment:
    attachment_id: UUID
    filename: str
    content_type: str
    storage_key: str


@dataclass(frozen=True)
class EnquiryContent:
    text: str
    attachments: tuple[CleanAttachment, ...]  # only attachments that passed inspection


class WorkflowStore(Protocol):
    def enquiry_content(self, tenant_id: UUID, enquiry_id: UUID) -> EnquiryContent | None: ...

    def start_run(self, tenant_id: UUID, enquiry_id: UUID, graph_version: str) -> UUID:
        """Return the run (thread) ID for this enquiry and graph version, creating it once."""
        ...

    def record_outcome(
        self,
        tenant_id: UUID,
        enquiry_id: UUID,
        run_id: UUID,
        outcome: ExtractionOutcome,
        details: Mapping[str, object],
    ) -> None:
        """Store the result and move the enquiry to the matching status. Safe to repeat."""
        ...
