"""Background worker process: claims durable jobs and runs their handlers.

Run: uv run python -m quotation_app.worker            (until Ctrl+C)
     uv run python -m quotation_app.worker --once     (drain available jobs, then exit)
Several workers can run at once; the queue gives each job to one worker at a time.
"""

import argparse
import logging
import time

from quotation_app.adapters.channels.simulated import SimulatedChannelNotifier
from quotation_app.adapters.delivery.api import ApiPullDelivery
from quotation_app.adapters.documents.pdf import ReportLabQuotationRenderer
from quotation_app.adapters.documents.text import PdfAndTextReader
from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.adapters.interpreters.factory import build_interpreter
from quotation_app.adapters.storage.local import LocalObjectStorage
from quotation_app.application.acceptance import (
    QuotationExpiryHandler,
    QuotationResponseService,
    ResponseNotificationHandler,
)
from quotation_app.application.delivery import QuotationDeliveryHandler
from quotation_app.application.jobs import JobRunner
from quotation_app.application.notifications import ApprovalNotificationHandler
from quotation_app.application.preparation import EnquiryPreparationHandler
from quotation_app.application.pricing import QuotationPricingService
from quotation_app.config import Settings
from quotation_app.domain.jobs import JobKind
from quotation_app.persistence.acceptance import SqlResponseStore
from quotation_app.persistence.channels import SqlNotificationStore
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.documents import SqlDeliveryStore
from quotation_app.persistence.intake import SqlPreparationStore
from quotation_app.persistence.jobs import SqlJobQueue
from quotation_app.persistence.quotations import SqlQuotationWorkflowStore
from quotation_app.persistence.seed import INDUSTRIAL_TENANT, OFFICE_TENANT
from quotation_app.persistence.tenancy import SqlPricingPolicyReader
from quotation_app.persistence.workflow import SqlWorkflowStore, open_checkpointer
from quotation_app.workflows.enquiry import (
    EnquiryWorkflowDeps,
    ExtractionJobHandler,
    build_enquiry_graph,
)
from quotation_app.workflows.quotation import (
    QuotationJobHandler,
    QuotationWorkflowDeps,
    build_quotation_graph,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="process available jobs and exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = Settings()
    engine = build_engine(settings.worker_url())
    storage = LocalObjectStorage(settings.storage_dir)
    interpreter = build_interpreter(
        settings.model_provider,
        settings.model_name,
        settings.ollama_base_url,
        settings.model_timeout_seconds,
        settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None,
    )
    # Only the simulated ERP exists until a pilot ERP is connected (M7).
    erp = SimulatedErp(demo_catalogues(INDUSTRIAL_TENANT, OFFICE_TENANT))
    workflow_store = SqlWorkflowStore(engine)
    quotation_store = SqlQuotationWorkflowStore(engine)
    pricing = QuotationPricingService(erp, SqlPricingPolicyReader(engine))
    # Manager channels: only the simulated one exists (dev/test), enabled with its secret.
    notifiers = (
        {"simulated": SimulatedChannelNotifier(settings.storage_dir / "simulated-channel")}
        if settings.simulated_channel_secret is not None
        else {}
    )
    # Customer delivery channels, by the channel the enquiry arrived on. Email, Telegram and
    # others are added here as adapters (see .docs/development/adding-channels.md).
    deliveries = QuotationDeliveryHandler(
        SqlDeliveryStore(engine),
        storage,
        ReportLabQuotationRenderer(),
        {channel.channel: channel for channel in (ApiPullDelivery(),)},
    )
    # Customer answers (M6): expiry at "valid until" and manager notices about answers.
    responses = SqlResponseStore(engine)
    expiry = QuotationExpiryHandler(QuotationResponseService(responses, pricing))
    response_notices = ResponseNotificationHandler(
        responses, SqlNotificationStore(engine), notifiers
    )
    logging.info("Enquiry interpreter: %s", settings.model_provider)
    try:
        with open_checkpointer(settings.worker_url()) as checkpointer:
            graph = build_enquiry_graph(
                EnquiryWorkflowDeps(workflow_store, storage, PdfAndTextReader(), interpreter, erp),
                checkpointer,
            )
            quotations = QuotationJobHandler(
                build_quotation_graph(
                    QuotationWorkflowDeps(quotation_store, pricing, responses), checkpointer
                ),
                quotation_store,
            )
            runner = JobRunner(
                SqlJobQueue(engine),
                {
                    JobKind.PREPARE_ENQUIRY: EnquiryPreparationHandler(
                        SqlPreparationStore(engine), storage
                    ),
                    JobKind.EXTRACT_REQUIREMENTS: ExtractionJobHandler(graph, workflow_store),
                    JobKind.DRAFT_QUOTATION: quotations,
                    JobKind.RESUME_QUOTATION: quotations,
                    JobKind.NOTIFY_APPROVERS: ApprovalNotificationHandler(
                        SqlNotificationStore(engine), notifiers
                    ),
                    JobKind.DELIVER_QUOTATION: deliveries,
                    JobKind.EXPIRE_QUOTATION: expiry,
                    JobKind.NOTIFY_RESPONSE: response_notices,
                },
            )
            while True:
                while runner.run_once():
                    pass
                if arguments.once:
                    return
                time.sleep(arguments.poll_seconds)
    except KeyboardInterrupt:
        logging.info("Worker stopped")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
