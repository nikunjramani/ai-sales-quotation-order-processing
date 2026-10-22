"""Create an API key for a tenant using owner credentials. The token is printed once only.

Example: uv run python scripts/create_api_key.py --tenant 11111111-1111-4111-8111-111111111111 \
             --role intake_service --name "website form"
Store the token in a secret manager; it cannot be recovered later, only revoked and replaced.
"""

import argparse
from uuid import UUID

from quotation_app.application.api_keys import generate_api_key
from quotation_app.config import Settings
from quotation_app.domain.tenancy import Role
from quotation_app.persistence.api_keys import insert_api_key, revoke_api_key
from quotation_app.persistence.database import build_engine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", type=UUID, required=True)
    parser.add_argument("--name", help="what the key is for")
    parser.add_argument("--role", type=Role, choices=list(Role), default=Role.INTAKE_SERVICE)
    parser.add_argument("--revoke", type=UUID, metavar="KEY_ID", help="revoke instead of create")
    arguments = parser.parse_args()

    engine = build_engine(Settings().migration_url())
    try:
        if arguments.revoke:
            revoked = revoke_api_key(engine, arguments.tenant, arguments.revoke)
            print("Revoked." if revoked else "No active key with that ID for this tenant.")
            return
        if not arguments.name:
            parser.error("--name is required when creating a key")
        key = generate_api_key()
        insert_api_key(
            engine, key.key_id, arguments.tenant, arguments.name, arguments.role, key.secret_sha256
        )
        print(f"Key ID: {key.key_id}\nToken (shown once): {key.token}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
