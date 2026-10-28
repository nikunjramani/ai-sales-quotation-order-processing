"""Score an enquiry interpreter on synthetic cases by running the real extraction workflow.

The same dataset judges every interpreter (rules or any AI model from settings), so switching
models is a measured decision. No database is needed: runs use in-memory storage and
checkpoints. Pricing is out of scope here; see the M1 calculator.
"""

import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from langgraph.checkpoint.memory import InMemorySaver

from quotation_app.adapters.documents.text import PdfAndTextReader
from quotation_app.domain.jobs import JobKind
from quotation_app.domain.requirements import ExtractionOutcome
from quotation_app.ports.erp import ErpReader
from quotation_app.ports.interpretation import EnquiryInterpreter, EnquiryTranscript
from quotation_app.ports.jobs import ClaimedJob
from quotation_app.ports.storage import ObjectNotFound
from quotation_app.ports.workflow import EnquiryContent
from quotation_app.workflows.enquiry import (
    EnquiryWorkflowDeps,
    ExtractionJobHandler,
    build_enquiry_graph,
)

DATASET = Path(__file__).resolve().parents[2] / "evals" / "enquiry_extraction.jsonl"

type ExpectedLine = tuple[str, Decimal, str]


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    tenant: str  # "industrial" or "office"
    text: str
    expected_outcome: ExtractionOutcome
    expected_lines: tuple[ExpectedLine, ...]
    # Optional: text that one of the customer questions must contain.
    expected_question: str | None = None


@dataclass(frozen=True)
class CaseResult:
    case: EvaluationCase
    outcome: str | None
    lines: tuple[ExpectedLine, ...]
    questions: tuple[str, ...]
    review_reasons: tuple[str, ...]
    seconds: float
    error: str | None

    @property
    def passed(self) -> bool:
        return (
            self.error is None
            and self.outcome == self.case.expected_outcome.value
            and sorted(self.lines) == sorted(self.case.expected_lines)
            and (
                self.case.expected_question is None
                or any(self.case.expected_question in question for question in self.questions)
            )
        )

    @property
    def invented_facts(self) -> int:
        return sum(
            "not supported by the customer's text" in reason for reason in self.review_reasons
        )


def load_cases(path: Path = DATASET) -> list[EvaluationCase]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        cases.append(
            EvaluationCase(
                name=data["name"],
                tenant=data["tenant"],
                text=data["text"],
                expected_outcome=ExtractionOutcome(data["expected_outcome"]),
                expected_lines=tuple(
                    (sku, Decimal(quantity), unit) for sku, quantity, unit in data["expected_lines"]
                ),
                expected_question=data.get("expected_question"),
            )
        )
    return cases


class InMemoryWorkflowStore:
    """WorkflowStore for evaluations and tests."""

    def __init__(self) -> None:
        self.contents: dict[tuple[UUID, UUID], EnquiryContent] = {}
        self.runs: dict[tuple[UUID, UUID, str, int], UUID] = {}
        self.outcomes: dict[UUID, tuple[ExtractionOutcome, Mapping[str, object]]] = {}

    def enquiry_content(self, tenant_id: UUID, enquiry_id: UUID) -> EnquiryContent | None:
        return self.contents.get((tenant_id, enquiry_id))

    def readings_today(
        self, tenant_id: UUID, enquiry_id: UUID, run_id: UUID, provider_keys: frozenset[str]
    ) -> int | None:
        return None

    def start_run(
        self, tenant_id: UUID, enquiry_id: UUID, graph_version: str, round: int = 1
    ) -> UUID:
        return self.runs.setdefault((tenant_id, enquiry_id, graph_version, round), uuid4())

    def record_outcome(
        self,
        tenant_id: UUID,
        enquiry_id: UUID,
        run_id: UUID,
        outcome: ExtractionOutcome,
        details: Mapping[str, object],
    ) -> bool:
        self.outcomes[enquiry_id] = (outcome, details)
        return True


class _NoAttachments:
    """Evaluation cases are text-only; any storage access is a test-setup error."""

    def put(self, key: str, data: bytes) -> None:
        raise ObjectNotFound(key)

    def get(self, key: str) -> bytes:
        raise ObjectNotFound(key)

    def exists(self, key: str) -> bool:
        return False

    def move(self, source: str, destination: str) -> None:
        raise ObjectNotFound(source)

    def delete(self, key: str) -> None:
        return None


def evaluate(
    interpreter: EnquiryInterpreter,
    erp: ErpReader,
    tenants: Mapping[str, UUID],
    cases: Sequence[EvaluationCase],
) -> list[CaseResult]:
    store = InMemoryWorkflowStore()
    deps = EnquiryWorkflowDeps(store, _NoAttachments(), PdfAndTextReader(), interpreter, erp)
    handler = ExtractionJobHandler(build_enquiry_graph(deps, InMemorySaver()), store)
    results = []
    for case in cases:
        tenant_id, enquiry_id = tenants[case.tenant], uuid4()
        store.contents[(tenant_id, enquiry_id)] = EnquiryContent(
            EnquiryTranscript.single(case.text), ()
        )
        job = ClaimedJob(
            uuid4(),
            tenant_id,
            JobKind.EXTRACT_REQUIREMENTS,
            {"enquiry_id": str(enquiry_id)},
            1,
            1,
            uuid4(),
            uuid4(),
        )
        started = time.perf_counter()
        error: str | None = None
        try:
            handler(job)
        except Exception as failure:  # noqa: BLE001 - reported per case, never hidden
            error = type(failure).__name__
        seconds = time.perf_counter() - started
        outcome, details = store.outcomes.get(enquiry_id, (None, {}))
        lines = details.get("lines", [])
        results.append(
            CaseResult(
                case=case,
                outcome=None if outcome is None else outcome.value,
                lines=tuple(
                    (str(line["sku"]), Decimal(str(line["quantity"])), str(line["unit"]))
                    for line in lines  # type: ignore[attr-defined]
                ),
                questions=tuple(str(q) for q in details.get("questions", [])),  # type: ignore[attr-defined]
                review_reasons=tuple(str(r) for r in details.get("review_reasons", [])),  # type: ignore[attr-defined]
                seconds=seconds,
                error=error,
            )
        )
    return results
