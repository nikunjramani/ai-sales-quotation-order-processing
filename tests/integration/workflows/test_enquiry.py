"""Extraction workflow on PostgreSQL: API -> worker -> LangGraph (Postgres checkpoints) -> M1."""

import base64
from collections.abc import Callable, Iterator, Mapping, Sequence
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import ProgrammingError

from quotation_app.adapters.documents.text import PdfAndTextReader
from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.adapters.interpreters.rules import RulesInterpreter
from quotation_app.adapters.storage.local import LocalObjectStorage
from quotation_app.api.app import create_app
from quotation_app.application.jobs import JobRunner
from quotation_app.application.preparation import EnquiryPreparationHandler
from quotation_app.application.pricing import QuotationPricingService
from quotation_app.config import Settings
from quotation_app.domain.catalogue import Product
from quotation_app.domain.jobs import JobKind
from quotation_app.domain.money import Money
from quotation_app.domain.pricing import PricedQuotation, RequestedLine
from quotation_app.domain.requirements import ExtractedRequirements, RequestedItem
from quotation_app.domain.tenancy import Role, TenantContext
from quotation_app.persistence.intake import SqlPreparationStore
from quotation_app.persistence.jobs import SqlJobQueue
from quotation_app.persistence.seed import INDUSTRIAL_TENANT, OFFICE_TENANT
from quotation_app.persistence.tenancy import SqlPricingPolicyReader, tenant_transaction
from quotation_app.persistence.workflow import SqlWorkflowStore, open_checkpointer
from quotation_app.ports.erp import ErpError, ErpErrorCode
from quotation_app.ports.interpretation import DocumentText
from quotation_app.workflows.enquiry import (
    EnquiryWorkflowDeps,
    ExtractionJobHandler,
    build_enquiry_graph,
)

type ApiKeyFactory = Callable[[UUID, Role], str]


class CountingInterpreter(RulesInterpreter):
    def __init__(self) -> None:
        self.extract_calls = 0

    def extract(self, text: str, documents: Sequence[DocumentText]) -> ExtractedRequirements:
        self.extract_calls += 1
        return super().extract(text, documents)

    def choose_product(self, item: RequestedItem, candidates: Sequence[Product]) -> str | None:
        return super().choose_product(item, candidates)


@pytest.fixture
def client(integration_settings: Settings, runtime_engine: Engine) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as http:
        yield http


@pytest.fixture
def erp() -> SimulatedErp:
    return SimulatedErp(demo_catalogues(INDUSTRIAL_TENANT, OFFICE_TENANT))


@pytest.fixture
def interpreter() -> CountingInterpreter:
    return CountingInterpreter()


@pytest.fixture
def worker(
    worker_engine: Engine,
    storage: LocalObjectStorage,
    integration_settings: Settings,
    erp: SimulatedErp,
    interpreter: CountingInterpreter,
) -> Iterator[JobRunner]:
    store = SqlWorkflowStore(worker_engine)
    with open_checkpointer(integration_settings.worker_url()) as checkpointer:
        deps = EnquiryWorkflowDeps(store, storage, PdfAndTextReader(), interpreter, erp)
        yield JobRunner(
            SqlJobQueue(worker_engine),
            {
                JobKind.PREPARE_ENQUIRY: EnquiryPreparationHandler(
                    SqlPreparationStore(worker_engine), storage
                ),
                JobKind.EXTRACT_REQUIREMENTS: ExtractionJobHandler(
                    build_enquiry_graph(deps, checkpointer), store
                ),
            },
        )


def submit(client: TestClient, token: str, body: Mapping[str, object], key: str) -> str:
    response = client.post(
        "/api/v1/enquiries",
        json=body,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": key},
    )
    assert response.status_code == 202, response.text
    return str(response.json()["enquiry_id"])


def drain(worker: JobRunner) -> None:
    while worker.run_once():
        pass


def test_enquiry_is_read_matched_and_priced_by_the_calculator(
    client: TestClient,
    worker: JobRunner,
    make_api_key: ApiKeyFactory,
    make_pdf: Callable[[list[str]], bytes],
    industrial_tenant: UUID,
    runtime_engine: Engine,
) -> None:
    token = make_api_key(industrial_tenant, Role.INTAKE_SERVICE)
    pdf = base64.b64encode(make_pdf(["Also add 12.5 metres of 2-core cable"])).decode()
    body = {
        "text": "Please quote 2 x IND-FAN-450 and 150 pcs M8 bolts for Pune.",
        "attachments": [
            {"filename": "extra.pdf", "content_type": "application/pdf", "content_base64": pdf}
        ],
    }
    enquiry_id = submit(client, token, body, "m3-ready-0001")
    drain(worker)  # prepare (inspect files) -> extract (LangGraph) -> done

    view = client.get(
        f"/api/v1/enquiries/{enquiry_id}", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert view["status"] == "ready_for_quotation"
    lines = view["extraction"]["lines"]
    assert lines == [
        {"sku": "IND-FAN-450", "quantity": "2", "unit": "each"},
        {"sku": "IND-BOLT-M8", "quantity": "150", "unit": "each"},
        {"sku": "IND-CABLE-2C", "quantity": "12.5", "unit": "metre"},
    ]

    # The workflow never prices. The M1 calculator turns the extracted lines into money.
    pricing = QuotationPricingService(
        SimulatedErp(demo_catalogues(INDUSTRIAL_TENANT, OFFICE_TENANT)),
        SqlPricingPolicyReader(runtime_engine),
    )
    sales = TenantContext(
        industrial_tenant, "sales@industrial.example", frozenset({Role.SALES_OPERATOR})
    )
    quote = pricing.price(
        sales, [RequestedLine(row["sku"], Decimal(row["quantity"]), row["unit"]) for row in lines]
    )
    assert isinstance(quote, PricedQuotation)
    # 2 x 4250.00 + 150 x 2.375 + 12.5 x 38.40 = 9336.25; 18% tax = 1680.53
    assert quote.total == Money(Decimal("11016.78"), "INR")


def test_unclear_request_waits_for_clarification(
    client: TestClient, worker: JobRunner, make_api_key: ApiKeyFactory, industrial_tenant: UUID
) -> None:
    token = make_api_key(industrial_tenant, Role.INTAKE_SERVICE)
    enquiry_id = submit(client, token, {"text": "Please quote 50 exhaust fans"}, "m3-unclear-1")
    drain(worker)
    view = client.get(
        f"/api/v1/enquiries/{enquiry_id}", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert view["status"] == "needs_clarification"
    assert view["extraction"]["lines"] == []
    assert "IND-FAN-600" in view["extraction"]["questions"][0]


def test_progress_survives_a_worker_restart(
    client: TestClient,
    make_api_key: ApiKeyFactory,
    industrial_tenant: UUID,
    worker_engine: Engine,
    storage: LocalObjectStorage,
    integration_settings: Settings,
    erp: SimulatedErp,
    interpreter: CountingInterpreter,
    owner_engine: Engine,
) -> None:
    token = make_api_key(industrial_tenant, Role.INTAKE_SERVICE)
    enquiry_id = UUID(submit(client, token, {"text": "Please quote 2 x IND-FAN-450"}, "m3-crash-1"))
    store = SqlWorkflowStore(worker_engine)
    prepare = EnquiryPreparationHandler(SqlPreparationStore(worker_engine), storage)
    queue = SqlJobQueue(worker_engine)
    JobRunner(queue, {JobKind.PREPARE_ENQUIRY: prepare}).run_once()

    def extraction_job_runner(checkpointer: object) -> JobRunner:
        deps = EnquiryWorkflowDeps(store, storage, PdfAndTextReader(), interpreter, erp)
        handler = ExtractionJobHandler(build_enquiry_graph(deps, checkpointer), store)  # type: ignore[arg-type]
        return JobRunner(queue, {JobKind.EXTRACT_REQUIREMENTS: handler})

    erp.failures["search_products"] = ErpError(ErpErrorCode.TEMPORARY_UNAVAILABLE, "down")
    with open_checkpointer(integration_settings.worker_url()) as first_process:
        extraction_job_runner(first_process).run_once()  # extract saved, match fails -> retry
    assert interpreter.extract_calls == 1

    del erp.failures["search_products"]
    with worker_engine.begin() as connection:  # skip the backoff wait
        connection.execute(text("UPDATE jobs SET run_at = now() WHERE status = 'pending'"))
    with open_checkpointer(integration_settings.worker_url()) as second_process:
        extraction_job_runner(second_process).run_once()
    assert interpreter.extract_calls == 1  # resumed from the PostgreSQL checkpoint

    with tenant_transaction(owner_engine, industrial_tenant) as connection:
        status = connection.execute(
            text("SELECT status FROM enquiries WHERE id = :id"), {"id": enquiry_id}
        ).scalar_one()
    assert status == "ready_for_quotation"


def test_checkpoints_and_runs_are_isolated(
    client: TestClient,
    worker: JobRunner,
    make_api_key: ApiKeyFactory,
    industrial_tenant: UUID,
    office_tenant: UUID,
    runtime_engine: Engine,
    worker_engine: Engine,
) -> None:
    token = make_api_key(industrial_tenant, Role.INTAKE_SERVICE)
    submit(client, token, {"text": "Please quote 2 x IND-FAN-450"}, "m3-isolation-1")
    drain(worker)
    with worker_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM checkpoints")).scalar_one() > 0
    with pytest.raises(ProgrammingError), runtime_engine.connect() as connection:
        connection.execute(text("SELECT count(*) FROM checkpoints"))
    for tenant, expected in ((industrial_tenant, 1), (office_tenant, 0)):
        with tenant_transaction(runtime_engine, tenant) as connection:
            runs = connection.execute(text("SELECT count(*) FROM workflow_runs")).scalar_one()
            assert runs == expected
