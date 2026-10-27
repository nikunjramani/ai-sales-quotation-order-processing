"""Background worker process: claims durable jobs and runs their handlers.

Run: uv run python -m quotation_app.worker            (until Ctrl+C)
     uv run python -m quotation_app.worker --once     (drain available jobs, then exit)
Several workers can run at once; the queue gives each job to one worker at a time.
Handlers are wired in quotation_app.composition, shared with the tests.
"""

import argparse
import logging
import time

from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.adapters.interpreters.factory import build_interpreter
from quotation_app.application.jobs import JobRunner
from quotation_app.composition import build_job_handlers, build_runtime
from quotation_app.config import Settings
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.jobs import SqlJobQueue
from quotation_app.persistence.seed import INDUSTRIAL_TENANT, OFFICE_TENANT
from quotation_app.persistence.workflow import open_checkpointer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="process available jobs and exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = Settings()
    engine = build_engine(settings.worker_url())
    interpreter = build_interpreter(
        settings.model,
        settings.model_api_key.get_secret_value() if settings.model_api_key else None,
        settings.model_options,
    )
    # Only the simulated ERP exists until a pilot ERP is connected (M7).
    erp = SimulatedErp(demo_catalogues(INDUSTRIAL_TENANT, OFFICE_TENANT))
    runtime = build_runtime(settings)
    logging.info("Enquiry interpreter: %s", settings.model or "rules (no AI)")
    logging.info("Providers: %s", ", ".join(p.key for p in runtime.registry.all()) or "none")
    try:
        with open_checkpointer(settings.worker_url()) as checkpointer:
            runner = JobRunner(
                SqlJobQueue(engine),
                build_job_handlers(settings, engine, runtime, checkpointer, interpreter, erp),
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
