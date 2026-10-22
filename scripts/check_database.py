"""Run migration and integration checks against the configured local development DB."""

import os
import subprocess
import sys

from sqlalchemy.engine import make_url

from quotation_app.config import Settings


def main() -> None:
    settings = Settings()
    runtime_url = settings.database_url.get_secret_value()
    owner_url = settings.migration_url()
    urls = [make_url(runtime_url), make_url(owner_url)]
    if settings.environment != "development" or any(
        url.host not in {"127.0.0.1", "localhost"} or url.database != "quotation_dev"
        for url in urls
    ):
        raise SystemExit("This helper only targets the local quotation_dev development database.")
    environment = dict(os.environ)
    environment.update(
        TEST_DATABASE_URL=runtime_url,
        TEST_MIGRATION_DATABASE_URL=owner_url,
    )
    commands = [
        ["alembic", "upgrade", "head"],
        ["alembic", "check"],
        ["pytest", "--run-integration"],
    ]
    for command in commands:
        subprocess.run([sys.executable, "-m", *command], check=True, env=environment)


if __name__ == "__main__":
    main()
