"""Create local-only credentials without printing them or overwriting an existing file."""

from pathlib import Path
from secrets import token_hex


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / ".env"
    admin, owner, app = (token_hex(24) for _ in range(3))
    content = (
        "# Generated local development credentials. Never commit this file.\n"
        f"POSTGRES_PASSWORD={admin}\n"
        f"POSTGRES_OWNER_PASSWORD={owner}\n"
        f"POSTGRES_APP_PASSWORD={app}\n"
        "QUOTATION_ENVIRONMENT=development\n"
        f"QUOTATION_DATABASE_URL=postgresql+psycopg://quotation_app:{app}"
        "@127.0.0.1:55432/quotation_dev\n"
        f"QUOTATION_MIGRATION_DATABASE_URL=postgresql+psycopg://quotation_owner:{owner}"
        "@127.0.0.1:55432/quotation_dev\n"
    )
    try:
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(content)
    except FileExistsError:
        raise SystemExit(".env already exists; left unchanged.") from None
    print("Created ignored .env for local PostgreSQL. No credentials printed.")


if __name__ == "__main__":
    main()
