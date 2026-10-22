"""Background worker process: claims durable jobs and runs their handlers.

Run: uv run python -m quotation_app.worker            (until Ctrl+C)
     uv run python -m quotation_app.worker --once     (drain available jobs, then exit)
Several workers can run at once; the queue gives each job to one worker at a time.
"""

import argparse
import logging
import time

from quotation_app.adapters.storage.local import LocalObjectStorage
from quotation_app.application.jobs import JobRunner
from quotation_app.application.preparation import EnquiryPreparationHandler
from quotation_app.config import Settings
from quotation_app.domain.jobs import JobKind
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.intake import SqlPreparationStore
from quotation_app.persistence.jobs import SqlJobQueue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="process available jobs and exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = Settings()
    engine = build_engine(settings.worker_url())
    storage = LocalObjectStorage(settings.storage_dir)
    runner = JobRunner(
        SqlJobQueue(engine),
        {JobKind.PREPARE_ENQUIRY: EnquiryPreparationHandler(SqlPreparationStore(engine), storage)},
    )
    try:
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
