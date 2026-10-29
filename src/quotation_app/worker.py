"""Background worker process: claims durable jobs and runs their handlers.

Run: uv run python -m quotation_app.worker            (until Ctrl+C)
     uv run python -m quotation_app.worker --once     (drain available jobs, then exit)
Several workers can run at once; the queue gives each job to one worker at a time.
Handlers are wired in quotation_app.composition, shared with the tests.
"""

import argparse
import logging
import time

from quotation_app.adapters.interpreters.factory import (
    build_interpreter,
    build_reply_classifier,
)
from quotation_app.application.jobs import JobRunner
from quotation_app.composition import build_job_handlers, build_runtime
from quotation_app.config import Settings
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.jobs import SqlJobQueue
from quotation_app.persistence.workflow import open_checkpointer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="process available jobs and exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = Settings()
    engine = build_engine(settings.worker_url())
    api_key = settings.model_api_key.get_secret_value() if settings.model_api_key else None
    interpreter = build_interpreter(settings.model, api_key, settings.model_options)
    reply_classifier = build_reply_classifier(settings.model, api_key, settings.model_options)
    runtime = build_runtime(settings, engine)
    logging.info("Enquiry interpreter: %s", settings.model or "rules (no AI)")
    logging.info("Providers: %s", ", ".join(p.key for p in runtime.registry.all()) or "none")
    try:
        with open_checkpointer(settings.worker_url()) as checkpointer:
            runner = JobRunner(
                SqlJobQueue(engine),
                build_job_handlers(
                    settings,
                    engine,
                    runtime,
                    checkpointer,
                    interpreter,
                    reply_classifier=reply_classifier,
                ),
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
