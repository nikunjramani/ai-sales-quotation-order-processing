"""Enquiry extraction workflow (LangGraph).

    START -> extract -> match -> assess -> ready | clarify | review -> END
                 \\________(model answer invalid)______/

- extract: read the enquiry and clean attachments, ask the interpreter for items, then check
  every item against the customer's own words (invented facts are flagged).
- match:   search the tenant's ERP per item; the interpreter may only pick among ERP results.
- assess:  deterministic rules decide ready / needs clarification / needs review.
- finish:  record the outcome on the enquiry.

Each step is checkpointed, so after a crash the job resumes at the step that failed instead of
asking the model again. State holds IDs and small summaries only; document text is never
checkpointed. Prices are not involved here: pricing stays with the M1 calculator.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from quotation_app.domain.catalogue import Product
from quotation_app.domain.jobs import PermanentJobError
from quotation_app.domain.requirements import (
    ExtractedRequirements,
    ExtractionOutcome,
    MatchStatus,
    ProductMatch,
    RequestedItem,
    assess,
    decide_match,
    unverified_items,
)
from quotation_app.domain.tenancy import Role, TenantContext
from quotation_app.ports.erp import ErpReader
from quotation_app.ports.interpretation import (
    DocumentReader,
    EnquiryInterpreter,
    InterpretationRejected,
)
from quotation_app.ports.jobs import ClaimedJob
from quotation_app.ports.storage import ObjectStorage
from quotation_app.ports.workflow import WorkflowStore

GRAPH_VERSION = "enquiry-extraction-v1"
SYSTEM_SUBJECT = "system:enquiry-workflow"
SEARCH_LIMIT = 5
INVALID_MODEL_ANSWER = "The model's answer was not in the required format"


class EnquiryState(TypedDict, total=False):
    tenant_id: str
    enquiry_id: str
    run_id: str
    rejected: bool
    items: list[dict[str, str | None]]
    unverified: list[int]
    unsupported_documents: list[str]
    matches: list[dict[str, object]]
    products: list[dict[str, str]]
    outcome: str
    lines: list[dict[str, str]]
    questions: list[str]
    review_reasons: list[str]


type EnquiryGraph = CompiledStateGraph[EnquiryState, None, EnquiryState, EnquiryState]


@dataclass(frozen=True)
class EnquiryWorkflowDeps:
    store: WorkflowStore
    storage: ObjectStorage
    reader: DocumentReader
    interpreter: EnquiryInterpreter
    erp: ErpReader


# Checkpointed state uses plain strings so it serialises safely and stays readable.
def _item_to_state(item: RequestedItem) -> dict[str, str | None]:
    return {
        "source_quote": item.source_quote,
        "product_text": item.product_text,
        "quantity": None if item.quantity is None else str(item.quantity),
        "unit": item.unit,
    }


def _item_from_state(data: dict[str, str | None]) -> RequestedItem:
    quantity = data["quantity"]
    return RequestedItem(
        source_quote=str(data["source_quote"]),
        product_text=str(data["product_text"]),
        quantity=None if quantity is None else Decimal(quantity),
        unit=data["unit"],
    )


def _product_to_state(product: Product) -> dict[str, str]:
    return {
        "sku": product.sku,
        "description": product.description,
        "unit": product.unit,
        "minimum_quantity": str(product.minimum_quantity),
        "quantity_step": str(product.quantity_step),
    }


def _product_from_state(data: dict[str, str]) -> Product:
    return Product(
        data["sku"],
        data["description"],
        data["unit"],
        Decimal(data["minimum_quantity"]),
        Decimal(data["quantity_step"]),
    )


def _ids(state: EnquiryState) -> tuple[UUID, UUID]:
    return UUID(state["tenant_id"]), UUID(state["enquiry_id"])


def build_enquiry_graph(
    deps: EnquiryWorkflowDeps, checkpointer: BaseCheckpointSaver[str]
) -> EnquiryGraph:
    def extract(state: EnquiryState) -> EnquiryState:
        tenant_id, enquiry_id = _ids(state)
        content = deps.store.enquiry_content(tenant_id, enquiry_id)
        if content is None:
            raise PermanentJobError("Enquiry not found for this tenant")
        documents = [
            deps.reader.read(item.filename, item.content_type, deps.storage.get(item.storage_key))
            for item in content.attachments
        ]
        unsupported = [
            f"{doc.name} ({doc.unsupported_reason})" for doc in documents if not doc.text
        ]
        try:
            requirements = deps.interpreter.extract(content.text, documents)
        except InterpretationRejected:
            return {
                "rejected": True,
                "items": [],
                "unverified": [],
                "unsupported_documents": unsupported,
            }
        sources = [content.text] + [doc.text for doc in documents if doc.text]
        return {
            "rejected": False,
            "items": [_item_to_state(item) for item in requirements.items],
            "unverified": unverified_items(requirements, sources),
            "unsupported_documents": unsupported,
        }

    def match(state: EnquiryState) -> EnquiryState:
        tenant_id, _ = _ids(state)
        # A read-only system identity: the workflow may look up products, nothing more.
        context = TenantContext(tenant_id, SYSTEM_SUBJECT, frozenset({Role.VIEWER}))
        matches: list[dict[str, object]] = []
        products: dict[str, Product] = {}
        for index, data in enumerate(state["items"]):
            if index in state["unverified"]:
                continue
            item = _item_from_state(data)
            candidates = deps.erp.search_products(context, item.product_text, SEARCH_LIMIT)
            chosen = (
                deps.interpreter.choose_product(item, candidates) if len(candidates) > 1 else None
            )
            decided = decide_match(index, candidates, chosen)
            products.update((product.sku, product) for product in candidates)
            matches.append(
                {
                    "item_index": index,
                    "status": decided.status.value,
                    "sku": decided.sku,
                    "candidate_skus": list(decided.candidate_skus),
                }
            )
        return {"matches": matches, "products": [_product_to_state(p) for p in products.values()]}

    def assess_step(state: EnquiryState) -> EnquiryState:
        if state.get("rejected"):
            reasons = [INVALID_MODEL_ANSWER] + [
                f"Attachment {name!r} could not be read; a person should check it"
                for name in state["unsupported_documents"]
            ]
            return {
                "outcome": ExtractionOutcome.NEEDS_REVIEW.value,
                "lines": [],
                "questions": [],
                "review_reasons": reasons,
            }
        result = assess(
            ExtractedRequirements(tuple(_item_from_state(data) for data in state["items"])),
            [
                ProductMatch(
                    int(str(data["item_index"])),
                    MatchStatus(str(data["status"])),
                    None if data["sku"] is None else str(data["sku"]),
                    tuple(str(sku) for sku in data["candidate_skus"]),  # type: ignore[attr-defined]
                )
                for data in state.get("matches", [])
            ],
            {data["sku"]: _product_from_state(data) for data in state.get("products", [])},
            state["unverified"],
            state["unsupported_documents"],
        )
        return {
            "outcome": result.outcome.value,
            "lines": [
                {"sku": line.sku, "quantity": str(line.quantity), "unit": line.unit}
                for line in result.lines
            ],
            "questions": list(result.questions),
            "review_reasons": list(result.review_reasons),
        }

    def record(state: EnquiryState, outcome: ExtractionOutcome) -> EnquiryState:
        tenant_id, enquiry_id = _ids(state)
        details: dict[str, object] = {
            "graph_version": GRAPH_VERSION,
            "items": state.get("items", []),
            "matches": state.get("matches", []),
            "lines": state.get("lines", []),
            "questions": state.get("questions", []),
            "review_reasons": state.get("review_reasons", []),
            "unsupported_documents": state.get("unsupported_documents", []),
        }
        deps.store.record_outcome(tenant_id, enquiry_id, UUID(state["run_id"]), outcome, details)
        return {}

    def ready(state: EnquiryState) -> EnquiryState:
        return record(state, ExtractionOutcome.READY_FOR_QUOTATION)

    def clarify(state: EnquiryState) -> EnquiryState:
        # Questions are stored for a person or a later channel adapter to send (M5/M7).
        return record(state, ExtractionOutcome.NEEDS_CLARIFICATION)

    def review(state: EnquiryState) -> EnquiryState:
        return record(state, ExtractionOutcome.NEEDS_REVIEW)

    graph = StateGraph(EnquiryState)
    graph.add_node("extract", extract)
    graph.add_node("match", match)
    graph.add_node("assess", assess_step)
    graph.add_node("ready", ready)
    graph.add_node("clarify", clarify)
    graph.add_node("review", review)
    graph.add_edge(START, "extract")
    graph.add_conditional_edges(
        "extract", lambda state: "assess" if state.get("rejected") else "match", ["match", "assess"]
    )
    graph.add_edge("match", "assess")
    graph.add_conditional_edges(
        "assess",
        lambda state: {
            ExtractionOutcome.READY_FOR_QUOTATION.value: "ready",
            ExtractionOutcome.NEEDS_CLARIFICATION.value: "clarify",
        }.get(state["outcome"], "review"),
        ["ready", "clarify", "review"],
    )
    for node in ("ready", "clarify", "review"):
        graph.add_edge(node, END)
    return graph.compile(checkpointer=checkpointer)


class ExtractionJobHandler:
    """Job handler: start the graph for an enquiry, or resume it from its last checkpoint."""

    def __init__(self, graph: EnquiryGraph, store: WorkflowStore) -> None:
        self._graph = graph
        self._store = store

    def __call__(self, job: ClaimedJob) -> None:
        try:
            enquiry_id = UUID(job.payload["enquiry_id"])
        except (KeyError, ValueError):
            raise PermanentJobError("Job payload has no valid enquiry_id") from None
        run_id = self._store.start_run(job.tenant_id, enquiry_id, GRAPH_VERSION)
        config: RunnableConfig = {"configurable": {"thread_id": str(run_id)}}
        snapshot = self._graph.get_state(config)
        if snapshot.values and not snapshot.next:
            return  # finished on an earlier attempt
        if snapshot.next:
            self._graph.invoke(None, config)  # resume after a crash
        else:
            start: EnquiryState = {
                "tenant_id": str(job.tenant_id),
                "enquiry_id": str(enquiry_id),
                "run_id": str(run_id),
            }
            self._graph.invoke(start, config)
