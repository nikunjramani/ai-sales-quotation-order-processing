"""Idempotently insert fictional tenants, people, memberships, policies and connections.

Runs with owner credentials, development/test only. Existing rows are left unchanged. Subjects
use the reserved .example domain. Each demo business gets one `simulated` connection (ADR 0018):
the fake manager phone and its demo catalogue. Phase 2: the demo businesses are live, each demo
person is a verified user and, when QUOTATION_DEMO_PASSWORD is set, can also sign in with that
password (user answer Q24); the dev login keeps working either way.
"""

import hashlib
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import Connection, func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from quotation_app.adapters.accounts.password import Argon2PasswordHasher
from quotation_app.adapters.providers.simulated.provider import SIGNING_SECRET
from quotation_app.adapters.providers.simulated.signing import hook_token
from quotation_app.composition import build_secret_store
from quotation_app.config import Settings
from quotation_app.domain.connections import Purpose
from quotation_app.domain.money import RoundingMode
from quotation_app.domain.tenancy import Role
from quotation_app.persistence.connections import ensure_connection
from quotation_app.persistence.database import build_engine
from quotation_app.persistence.models import (
    ConnectionRow,
    Membership,
    Tenant,
    TenantPricingPolicy,
    TenantProfile,
    User,
    UserCredential,
)
from quotation_app.ports.secrets import SecretNotFound, SecretStore

INDUSTRIAL_TENANT = UUID("11111111-1111-4111-8111-111111111111")
OFFICE_TENANT = UUID("22222222-2222-4222-8222-222222222222")

DEMO_TENANTS = (
    (INDUSTRIAL_TENANT, "Demo Industrial Supplies"),
    (OFFICE_TENANT, "Demo Office Equipment"),
)

DEMO_MEMBERSHIPS = (
    (INDUSTRIAL_TENANT, "admin@industrial.example", Role.ADMINISTRATOR),
    (INDUSTRIAL_TENANT, "sales@industrial.example", Role.SALES_OPERATOR),
    (INDUSTRIAL_TENANT, "manager@industrial.example", Role.APPROVER),
    (INDUSTRIAL_TENANT, "viewer@industrial.example", Role.VIEWER),
    (OFFICE_TENANT, "sales@office.example", Role.SALES_OPERATOR),
)

# Synthetic policies for learning; real tax/rounding rules come from each pilot business.
DEMO_POLICIES = (
    (INDUSTRIAL_TENANT, "INR", 2, RoundingMode.HALF_UP, Decimal("0.18")),
    (OFFICE_TENANT, "EUR", 2, RoundingMode.HALF_EVEN, Decimal("0.19")),
)


# The development provider (dev-only, refused in production) and its demo catalogue names.
SIMULATED_PROVIDER = "simulated"
SIMULATED_ACCOUNT = "simulated-local"
DEMO_CONNECTIONS = (
    (INDUSTRIAL_TENANT, "industrial"),
    (OFFICE_TENANT, "office"),
)


def _set_tenant(connection: Connection, tenant_id: UUID) -> None:
    # FORCE RLS also applies to the owner. Context is transaction-local.
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


def _enable_hook(
    connection: Connection,
    tenant_id: UUID,
    connection_id: UUID,
    secret: str,
    secrets: SecretStore,
) -> None:
    """Give the demo phone connection its webhook (development, when the dev secret is set).

    The signing secret is the development secret, stored in the secret store (only its
    reference in the database). The URL token is derived from it, so tools can compute the
    hook URL from .env; only the token's SHA-256 is stored.
    """
    refs = connection.execute(
        select(ConnectionRow.secret_refs).where(
            ConnectionRow.tenant_id == tenant_id, ConnectionRow.id == connection_id
        )
    ).scalar_one()
    reference = refs.get(SIGNING_SECRET)
    try:
        current = None if reference is None else secrets.get(tenant_id, reference)
    except SecretNotFound:
        current = None
    if current != secret:
        reference = secrets.put(tenant_id, SIGNING_SECRET, secret)
    token = hook_token(secret, connection_id)
    connection.execute(
        update(ConnectionRow)
        .where(ConnectionRow.tenant_id == tenant_id, ConnectionRow.id == connection_id)
        .values(
            secret_refs={**refs, SIGNING_SECRET: reference},
            webhook_token_sha256=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )
    )


def _demo_people(connection: Connection, password: str | None) -> None:
    """Verified users for the demo subjects (their email), before memberships reference them."""
    hasher = Argon2PasswordHasher() if password is not None else None
    for subject in sorted({subject for _, subject, _ in DEMO_MEMBERSHIPS}):
        connection.execute(
            insert(User)
            .values(
                id=uuid5(NAMESPACE_URL, f"demo-user:{subject}"),
                subject=subject,
                email=subject,
                email_normalized=subject,
                email_verified_at=func.now(),
            )
            .on_conflict_do_nothing(index_elements=["subject"])
        )
        # People backfilled by migration 0010 exist already, unverified.
        user_id = connection.execute(
            update(User)
            .where(User.subject == subject)
            .values(email_verified_at=func.coalesce(User.email_verified_at, func.now()))
            .returning(User.id)
        ).scalar_one()
        if hasher is None or password is None:
            continue
        current = connection.execute(
            select(UserCredential.password_hash).where(UserCredential.user_id == user_id)
        ).scalar_one_or_none()
        if current is not None and hasher.verify(current, password):
            continue
        new_hash = hasher.hash(password)
        connection.execute(
            insert(UserCredential)
            .values(user_id=user_id, password_hash=new_hash)
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={"password_hash": new_hash, "password_changed_at": func.now()},
            )
        )


def seed_demo_tenants(settings: Settings) -> None:
    if settings.environment not in {"development", "test"}:
        raise ValueError("Demo data seeding is disabled outside development/test")
    engine = build_engine(settings.migration_url())
    try:
        with engine.begin() as connection:
            demo_password = settings.demo_password
            _demo_people(connection, demo_password.get_secret_value() if demo_password else None)
            for tenant_id, name in DEMO_TENANTS:
                _set_tenant(connection, tenant_id)
                connection.execute(
                    insert(Tenant)
                    .values(id=tenant_id, name=name, status="active", went_live_at=func.now())
                    .on_conflict_do_nothing(index_elements=["id"])
                )
                # Empty PDF details: demo PDFs keep printing only the business name.
                connection.execute(
                    insert(TenantProfile)
                    .values(tenant_id=tenant_id)
                    .on_conflict_do_nothing(index_elements=["tenant_id"])
                )
            for tenant_id, subject, role in DEMO_MEMBERSHIPS:
                _set_tenant(connection, tenant_id)
                connection.execute(
                    insert(Membership)
                    .values(id=uuid4(), tenant_id=tenant_id, subject=subject, role=role.value)
                    .on_conflict_do_nothing(index_elements=["tenant_id", "subject", "role"])
                )
            for tenant_id, currency, minor_units, rounding, tax_rate in DEMO_POLICIES:
                _set_tenant(connection, tenant_id)
                connection.execute(
                    insert(TenantPricingPolicy)
                    .values(
                        tenant_id=tenant_id,
                        version=1,
                        currency=currency,
                        minor_units=minor_units,
                        rounding_mode=rounding.value,
                        tax_rate=tax_rate,
                        max_price_age_seconds=900,
                        max_stock_age_seconds=300,
                    )
                    .on_conflict_do_nothing(index_elements=["tenant_id"])
                )
            for tenant_id, catalogue in DEMO_CONNECTIONS:
                _set_tenant(connection, tenant_id)
                connection_id = ensure_connection(
                    connection,
                    tenant_id=tenant_id,
                    provider_key=SIMULATED_PROVIDER,
                    account_ref=SIMULATED_ACCOUNT,
                    display_name="Simulated phone and demo catalogue",
                    purposes=[Purpose.MANAGER_APPROVALS, Purpose.CATALOGUE],
                    created_by="seed",
                    config={"catalogue": catalogue},
                )
                if settings.simulated_channel_secret is not None:
                    _enable_hook(
                        connection,
                        tenant_id,
                        connection_id,
                        settings.simulated_channel_secret.get_secret_value(),
                        build_secret_store(settings),
                    )
    finally:
        engine.dispose()


def main() -> None:
    seed_demo_tenants(Settings())
    print(
        "Synthetic tenants, memberships, policies and connections are present. "
        "Existing rows unchanged."
    )


if __name__ == "__main__":
    main()
