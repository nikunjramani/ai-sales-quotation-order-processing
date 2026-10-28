"""Accounts and onboarding (phase 2): people, passwords, email links, invitations, business
status, PDF details, audit, rate limits and four narrow database functions.

- users is global (a person may belong to several businesses). Narrow GUC-scoped policies show
  the API role only: the signed-in person (app.subject), the address being signed in with
  (app.user_email), the person a credential or token belongs to (app.user_id), and the members
  of the current business (app.tenant_id). The worker never reads users or credentials: every
  email row carries its own recipient.
- Email links (verification, reset, invitation): only SHA-256 hashes, written by the worker at
  send time; the API finds a row only by the hash it presents (app.account_token_sha256).
- account_notices: emails without a link ("someone tried to sign up", "password changed").
- Business status setting_up -> active (Go live) only; suspension only with owner credentials.
- Pricing "set later": the commercial columns may be NULL; complete = all six set.
- The runtime role still cannot insert tenants or memberships (ADR 0002): create_business,
  accept_invitation, change_member_roles and remove_member are SECURITY DEFINER functions with a
  fixed search_path. They trust only app.subject for "who is calling" and check it against
  stored rows; errors: 42501 not allowed, QA001 invitation not usable, QA002 last administrator.
- rate_limit_counters: fixed-window counters shared by every API process (user answer Q5);
  keys are SHA-256 hashes.
- jobs.tenant_id may be NULL, only for send_account_email.

Backfill: one user per membership subject (the email when the subject looks like one, never
verified); existing businesses become active (went_live_at = created_at) with an empty profile.
Downgrade loses passwords, email links, invitations, audit events, PDF details and statuses;
businesses created through sign-up stay, but their incomplete pricing rows are deleted.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_accounts"
down_revision = "0009_outbound_messages"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_SUBJECT = "NULLIF(current_setting('app.subject', true), '')"
_USER_ID = "NULLIF(current_setting('app.user_id', true), '')::uuid"
_USER_EMAIL = "NULLIF(current_setting('app.user_email', true), '')"
_TOKEN = "NULLIF(current_setting('app.account_token_sha256', true), '')"
_REF_ID = "NULLIF(current_setting('app.account_ref_id', true), '')::uuid"
_PEOPLE_ROLES = "'administrator', 'sales_operator', 'approver', 'viewer'"
_EMAIL_STATUSES = "'pending', 'sending', 'sent', 'failed', 'unknown'"
_ADMIN_ACTIONS = (
    "'business_created', 'went_live', 'status_changed', 'details_changed', 'profile_changed', "
    "'logo_changed', 'pricing_changed', 'member_invited', 'invitation_resent', "
    "'invitation_revoked', 'invitation_accepted', 'member_roles_changed', 'member_removed', "
    "'api_key_created', 'api_key_revoked'"
)
_NOW = sa.text("now()")
_FUNCTIONS = (
    "create_business(uuid, text, text, text, text, numeric, integer)",
    "accept_invitation(text, uuid)",
    "change_member_roles(uuid, uuid, text[])",
    "remove_member(uuid, uuid)",
)


def _force_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _tenant_isolation(table: str) -> None:
    _force_rls(table)
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
    )


def _policy(name: str, table: str, commands: tuple[str, ...], role: str, using: str) -> None:
    """One policy per command (PostgreSQL allows one command or ALL per policy)."""
    for command in commands:
        check = f" WITH CHECK ({using})" if command in ("UPDATE", "ALL") else ""
        if command == "INSERT":
            op.execute(
                f"CREATE POLICY {name}_insert ON {table} FOR INSERT TO {role} WITH CHECK ({using})"
            )
            continue
        op.execute(
            f"CREATE POLICY {name}_{command.lower()} ON {table} FOR {command} TO {role} "
            f"USING ({using}){check}"
        )


def _email_link_table(table: str) -> None:
    """email_verifications and password_resets have the same shape and rules."""
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(254), nullable=False),
        sa.Column("token_sha256", sa.String(64), nullable=True),
        sa.Column("email_status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=f"fk_{table}_user_id_users"),
        sa.UniqueConstraint("token_sha256", name=f"uq_{table}_token_sha256"),
        sa.CheckConstraint(f"email_status IN ({_EMAIL_STATUSES})", name=f"ck_{table}_email_status"),
    )
    op.create_index(
        f"uq_{table}_one_open",
        table,
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("consumed_at IS NULL AND revoked_at IS NULL"),
    )
    _force_rls(table)
    _policy(
        "own_rows", table, ("SELECT", "INSERT", "UPDATE"), "quotation_app", f"user_id = {_USER_ID}"
    )
    _policy(
        "token_lookup", table, ("SELECT", "UPDATE"), "quotation_app", f"token_sha256 = {_TOKEN}"
    )
    _policy("worker_send", table, ("SELECT", "UPDATE"), "quotation_worker", f"id = {_REF_ID}")
    op.execute(
        f"GRANT SELECT, INSERT (id, user_id, email_normalized), UPDATE (consumed_at, revoked_at) "
        f"ON {table} TO quotation_app"
    )
    op.execute(
        f"GRANT SELECT, UPDATE (token_sha256, expires_at, email_status, sent_at) "
        f"ON {table} TO quotation_worker"
    )


def upgrade() -> None:
    _users()
    _email_link_table("email_verifications")
    _email_link_table("password_resets")
    _account_notices()
    _tenants()
    _profiles_and_pricing()
    _invitations_and_audit()
    _other_tables()
    _functions()


def _users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("email_normalized", sa.String(254), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("subject", name="uq_users_subject"),
        sa.CheckConstraint(
            "email_normalized = lower(email_normalized)", name="ck_users_email_normalized"
        ),
    )
    op.create_index(
        "uq_users_email_normalized",
        "users",
        ["email_normalized"],
        unique=True,
        postgresql_where=sa.text("email_normalized IS NOT NULL"),
    )
    _force_rls("users")
    _policy("users_self", "users", ("SELECT", "UPDATE"), "quotation_app", f"subject = {_SUBJECT}")
    _policy(
        "users_email_lookup",
        "users",
        ("SELECT",),
        "quotation_app",
        f"email_normalized = {_USER_EMAIL}",
    )
    _policy(
        "users_signup",
        "users",
        ("INSERT",),
        "quotation_app",
        f"email_normalized = {_USER_EMAIL} AND subject = 'user:' || id::text",
    )
    _policy("users_by_id", "users", ("SELECT", "UPDATE"), "quotation_app", f"id = {_USER_ID}")
    # Member lists: people who belong to the current business (memberships RLS applies inside).
    _policy(
        "users_tenant_directory",
        "users",
        ("SELECT",),
        "quotation_app",
        "EXISTS (SELECT 1 FROM memberships m WHERE m.subject = users.subject "
        f"AND m.{_TENANT_FILTER})",
    )
    # Seed and the definer functions (which check the caller themselves).
    _policy("users_owner", "users", ("ALL",), "quotation_owner", "true")
    op.execute(
        "GRANT SELECT, INSERT (id, subject, email, email_normalized, display_name), "
        "UPDATE (display_name, email_verified_at, updated_at) ON users TO quotation_app"
    )

    # Backfill: one person per existing membership subject (the demo people).
    op.execute("ALTER TABLE memberships NO FORCE ROW LEVEL SECURITY")
    op.execute(
        "INSERT INTO users (id, subject, email, email_normalized) "
        "SELECT gen_random_uuid(), subject, "
        "CASE WHEN subject LIKE '%_@_%' THEN subject END, "
        "CASE WHEN subject LIKE '%_@_%' THEN lower(subject) END "
        "FROM (SELECT DISTINCT subject FROM memberships) AS s"
    )
    op.execute("ALTER TABLE memberships FORCE ROW LEVEL SECURITY")
    op.create_foreign_key(
        "fk_memberships_subject_users", "memberships", "users", ["subject"], ["subject"]
    )

    op.create_table(
        "user_credentials",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "password_changed_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_credentials"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_credentials_user_id_users"
        ),
        sa.CheckConstraint("password_hash LIKE '$argon2id$%'", name="ck_user_credentials_argon2id"),
    )
    _force_rls("user_credentials")
    _policy(
        "credentials_by_user",
        "user_credentials",
        ("SELECT", "INSERT", "UPDATE"),
        "quotation_app",
        f"user_id = {_USER_ID}",
    )
    _policy("credentials_owner", "user_credentials", ("ALL",), "quotation_owner", "true")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (password_hash, password_changed_at) "
        "ON user_credentials TO quotation_app"
    )


def _account_notices() -> None:
    op.create_table(
        "account_notices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(254), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("email_status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_account_notices"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_account_notices_user_id_users"),
        sa.CheckConstraint(
            "purpose IN ('account_exists', 'password_changed')", name="ck_account_notices_purpose"
        ),
        sa.CheckConstraint(
            f"email_status IN ({_EMAIL_STATUSES})", name="ck_account_notices_email_status"
        ),
    )
    _force_rls("account_notices")
    _policy("own_rows", "account_notices", ("INSERT",), "quotation_app", f"user_id = {_USER_ID}")
    _policy(
        "worker_send",
        "account_notices",
        ("SELECT", "UPDATE"),
        "quotation_worker",
        f"id = {_REF_ID}",
    )
    op.execute(
        "GRANT INSERT (id, user_id, email_normalized, purpose) ON account_notices TO quotation_app"
    )
    op.execute(
        "GRANT SELECT, UPDATE (email_status, sent_at) ON account_notices TO quotation_worker"
    )


def _tenants() -> None:
    # Existing businesses are live already; only new ones start in setting_up.
    op.add_column(
        "tenants",
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
    )
    op.add_column("tenants", sa.Column("country", sa.String(2), nullable=True))
    op.add_column("tenants", sa.Column("time_zone", sa.String(64), nullable=True))
    op.add_column("tenants", sa.Column("created_by", sa.String(200), nullable=True))
    op.add_column("tenants", sa.Column("went_live_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )
    op.execute("ALTER TABLE tenants NO FORCE ROW LEVEL SECURITY")
    op.execute("UPDATE tenants SET went_live_at = created_at")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.alter_column("tenants", "status", server_default="setting_up")
    op.create_check_constraint(
        "ck_tenants_status", "tenants", "status IN ('setting_up', 'active', 'suspended')"
    )
    op.create_check_constraint("ck_tenants_country", "tenants", "country ~ '^[A-Z]{2}$'")
    # Go live is the only status change the API may make (Q12); suspension needs the owner (Q13).
    op.execute(
        "CREATE FUNCTION guard_tenant_status() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN "
        "IF NEW.status IS DISTINCT FROM OLD.status "
        "AND NOT (OLD.status = 'setting_up' AND NEW.status = 'active') "
        "AND current_user <> 'quotation_owner' THEN "
        "RAISE EXCEPTION 'This status change is not allowed' USING ERRCODE = '42501'; "
        "END IF; RETURN NEW; END $$"
    )
    op.execute(
        "CREATE TRIGGER tenants_status_guard BEFORE UPDATE ON tenants "
        "FOR EACH ROW EXECUTE FUNCTION guard_tenant_status()"
    )
    op.execute(
        "GRANT UPDATE (name, country, time_zone, status, went_live_at, updated_at) "
        "ON tenants TO quotation_app"
    )


def _profiles_and_pricing() -> None:
    op.create_table(
        "tenant_profiles",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(200), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("tax_id_label", sa.String(32), nullable=True),
        sa.Column("tax_id", sa.String(64), nullable=True),
        sa.Column("logo_storage_key", sa.String(300), nullable=True),
        sa.Column("logo_sha256", sa.String(64), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", name="pk_tenant_profiles"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_tenant_profiles_tenant_id_tenants"
        ),
        sa.CheckConstraint(
            "(logo_storage_key IS NULL) = (logo_sha256 IS NULL)", name="ck_tenant_profiles_logo"
        ),
        sa.CheckConstraint("version >= 1", name="ck_tenant_profiles_version"),
    )
    _tenant_isolation("tenant_profiles")
    op.execute("ALTER TABLE tenant_profiles NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants NO FORCE ROW LEVEL SECURITY")
    op.execute("INSERT INTO tenant_profiles (tenant_id) SELECT id FROM tenants")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_profiles FORCE ROW LEVEL SECURITY")
    op.execute(
        "GRANT SELECT, UPDATE (legal_name, address, tax_id_label, tax_id, logo_storage_key, "
        "logo_sha256, version, updated_by, updated_at) ON tenant_profiles TO quotation_app"
    )
    op.execute("GRANT SELECT ON tenant_profiles TO quotation_worker")

    # Pricing "set later" (Q14): commercial values may be missing until the manager saves them.
    for column in (
        "currency",
        "minor_units",
        "rounding_mode",
        "tax_rate",
        "max_price_age_seconds",
        "max_stock_age_seconds",
    ):
        op.alter_column("tenant_pricing_policies", column, nullable=True)
    op.add_column("tenant_pricing_policies", sa.Column("updated_by", sa.String(200), nullable=True))
    op.execute(
        "GRANT UPDATE (version, currency, minor_units, rounding_mode, tax_rate, "
        "max_price_age_seconds, max_stock_age_seconds, quote_validity_days, updated_by, "
        "updated_at) ON tenant_pricing_policies TO quotation_app"
    )


def _invitations_and_audit() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("email_normalized", sa.String(254), nullable=False),
        sa.Column("roles", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("invited_by", sa.String(200), nullable=False),
        sa.Column("token_sha256", sa.String(64), nullable=True),
        sa.Column("email_status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(200), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_invitations"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_invitations_tenant_id_tenants"
        ),
        sa.UniqueConstraint("token_sha256", name="uq_invitations_token_sha256"),
        sa.CheckConstraint(
            f"cardinality(roles) >= 1 AND roles <@ ARRAY[{_PEOPLE_ROLES}]::text[]",
            name="ck_invitations_roles",
        ),
        sa.CheckConstraint(
            f"email_status IN ({_EMAIL_STATUSES})", name="ck_invitations_email_status"
        ),
    )
    op.create_index(
        "uq_invitations_one_open",
        "invitations",
        ["tenant_id", "email_normalized"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )
    _tenant_isolation("invitations")
    # Preview (API) and accept_invitation (owner) find a row only by the presented token hash.
    _policy(
        "invitation_token_lookup",
        "invitations",
        ("SELECT",),
        "quotation_app",
        f"token_sha256 = {_TOKEN}",
    )
    _policy(
        "invitation_token_owner",
        "invitations",
        ("SELECT",),
        "quotation_owner",
        f"token_sha256 = {_TOKEN}",
    )
    op.execute(
        "GRANT SELECT, INSERT (id, tenant_id, email, email_normalized, roles, invited_by), "
        "UPDATE (revoked_at, revoked_by, email_status, token_sha256, expires_at) "
        "ON invitations TO quotation_app"
    )
    op.execute(
        "GRANT SELECT, UPDATE (token_sha256, expires_at, email_status, sent_at) "
        "ON invitations TO quotation_worker"
    )

    op.create_table(
        "admin_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("actor_subject", sa.String(200), nullable=False),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("target", sa.String(200), nullable=True),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_admin_events"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_admin_events_tenant_id_tenants"
        ),
        sa.CheckConstraint(f"action IN ({_ADMIN_ACTIONS})", name="ck_admin_events_action"),
    )
    op.create_index("ix_admin_events_tenant_created", "admin_events", ["tenant_id", "created_at"])
    _tenant_isolation("admin_events")
    op.execute(
        "CREATE TRIGGER admin_events_immutable BEFORE UPDATE OR DELETE ON admin_events "
        "FOR EACH ROW EXECUTE FUNCTION reject_change()"
    )
    op.execute("GRANT SELECT, INSERT ON admin_events TO quotation_app")


def _other_tables() -> None:
    # API keys from the portal (Q17): the runtime role creates and revokes them in its tenant,
    # together with their `api` connection.
    op.add_column("api_keys", sa.Column("created_by", sa.String(200), nullable=True))
    op.add_column("api_keys", sa.Column("revoked_by", sa.String(200), nullable=True))
    op.execute(
        "GRANT INSERT (id, tenant_id, name, role, secret_sha256, created_by), "
        "UPDATE (revoked_at, revoked_by) ON api_keys TO quotation_app"
    )
    op.execute(
        "GRANT INSERT (id, tenant_id, provider_key, display_name, purposes, config, account_ref, "
        "status, created_by), UPDATE (status, updated_at) ON connections TO quotation_app"
    )
    op.execute("GRANT INSERT ON connection_events TO quotation_app")

    # Sign-up and reset emails belong to no business.
    op.alter_column("jobs", "tenant_id", nullable=True)
    op.create_check_constraint(
        "ck_jobs_tenant", "jobs", "tenant_id IS NOT NULL OR kind = 'send_account_email'"
    )
    op.execute(
        "CREATE POLICY account_email_jobs ON jobs FOR INSERT TO quotation_app "
        "WITH CHECK (tenant_id IS NULL AND kind = 'send_account_email')"
    )

    # Sign out everywhere after a password reset or change.
    _policy(
        "session_for_subject",
        "user_sessions",
        ("SELECT", "UPDATE"),
        "quotation_app",
        f"subject = {_SUBJECT}",
    )

    op.create_table(
        "rate_limit_counters",
        sa.Column("rule", sa.String(32), nullable=False),
        sa.Column("key_sha256", sa.String(64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("rule", "key_sha256", name="pk_rate_limit_counters"),
        sa.CheckConstraint("hits >= 1", name="ck_rate_limit_counters_hits"),
    )
    op.create_index("ix_rate_limit_counters_expires", "rate_limit_counters", ["expires_at"])
    _force_rls("rate_limit_counters")
    _policy("rate_limits_app", "rate_limit_counters", ("ALL",), "quotation_app", "true")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON rate_limit_counters TO quotation_app")


_CREATE_BUSINESS = f"""
CREATE FUNCTION create_business(
    p_user_id uuid, p_name text, p_country text, p_time_zone text,
    p_currency text, p_tax_rate numeric, p_quote_validity_days integer
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
    v_subject text := {_SUBJECT};
    v_previous text := current_setting('app.tenant_id', true);
    v_tenant uuid := gen_random_uuid();  -- never a parameter: cannot target an existing business
    v_name text := btrim(p_name);
BEGIN
    IF v_subject IS NULL OR NOT EXISTS (
        SELECT 1 FROM users WHERE id = p_user_id AND subject = v_subject
        AND email_verified_at IS NOT NULL AND disabled_at IS NULL
    ) THEN
        RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
    END IF;
    IF v_name IS NULL OR length(v_name) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'invalid business name' USING ERRCODE = '22023';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name = p_time_zone) THEN
        RAISE EXCEPTION 'unknown time zone' USING ERRCODE = '22023';
    END IF;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    INSERT INTO tenants (id, name, status, country, time_zone, created_by)
    VALUES (v_tenant, v_name, 'setting_up', p_country, p_time_zone, v_subject);
    INSERT INTO memberships (id, tenant_id, subject, role) VALUES
        (gen_random_uuid(), v_tenant, v_subject, 'administrator'),
        (gen_random_uuid(), v_tenant, v_subject, 'approver');
    INSERT INTO tenant_pricing_policies
        (tenant_id, version, currency, tax_rate, quote_validity_days, updated_by)
    VALUES (v_tenant, 1, p_currency, p_tax_rate, p_quote_validity_days, v_subject);
    INSERT INTO tenant_profiles (tenant_id) VALUES (v_tenant);
    INSERT INTO admin_events (id, tenant_id, actor_subject, action, details)
    VALUES (gen_random_uuid(), v_tenant, v_subject, 'business_created',
            jsonb_build_object('name', v_name));
    PERFORM set_config('app.tenant_id', COALESCE(v_previous, ''), true);
    RETURN v_tenant;
END $$
"""

_ACCEPT_INVITATION = f"""
CREATE FUNCTION accept_invitation(p_token_sha256 text, p_user_id uuid)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
    v_subject text := {_SUBJECT};
    v_previous text := current_setting('app.tenant_id', true);
    v_previous_token text := current_setting('app.account_token_sha256', true);
    v_tenant uuid;
    v_invitation invitations%ROWTYPE;
BEGIN
    PERFORM set_config('app.account_token_sha256', COALESCE(p_token_sha256, ''), true);
    SELECT tenant_id INTO v_tenant FROM invitations WHERE token_sha256 = p_token_sha256;
    PERFORM set_config('app.account_token_sha256', COALESCE(v_previous_token, ''), true);
    IF v_tenant IS NULL OR v_subject IS NULL THEN
        RAISE EXCEPTION 'invitation not usable' USING ERRCODE = 'QA001';
    END IF;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    PERFORM 1 FROM tenants WHERE id = v_tenant AND status <> 'suspended' FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'invitation not usable' USING ERRCODE = 'QA001';
    END IF;
    SELECT * INTO v_invitation FROM invitations
    WHERE tenant_id = v_tenant AND token_sha256 = p_token_sha256 FOR UPDATE;
    IF v_invitation.accepted_at IS NOT NULL OR v_invitation.revoked_at IS NOT NULL
       OR v_invitation.expires_at IS NULL OR v_invitation.expires_at <= now()
       OR NOT EXISTS (
           SELECT 1 FROM users WHERE id = p_user_id AND subject = v_subject
           AND disabled_at IS NULL AND email_normalized = v_invitation.email_normalized
       ) THEN
        RAISE EXCEPTION 'invitation not usable' USING ERRCODE = 'QA001';
    END IF;
    -- The link in the email proves control of the address.
    UPDATE users SET email_verified_at = COALESCE(email_verified_at, now()), updated_at = now()
    WHERE id = p_user_id;
    INSERT INTO memberships (id, tenant_id, subject, role)
    SELECT gen_random_uuid(), v_tenant, v_subject, role FROM unnest(v_invitation.roles) AS role
    ON CONFLICT (tenant_id, subject, role) DO NOTHING;
    UPDATE invitations SET accepted_at = now(), accepted_by = v_subject
    WHERE tenant_id = v_tenant AND id = v_invitation.id;
    INSERT INTO admin_events (id, tenant_id, actor_subject, action, target, details)
    VALUES (gen_random_uuid(), v_tenant, v_subject, 'invitation_accepted', p_user_id::text,
            jsonb_build_object('invitation', v_invitation.id, 'roles', v_invitation.roles));
    PERFORM set_config('app.tenant_id', COALESCE(v_previous, ''), true);
    RETURN v_tenant;
END $$
"""

# Shared start of the two member functions: lock the business (serialises concurrent changes,
# so two administrators removing each other cannot both succeed), check it is not suspended,
# and find the target's subject.
_MEMBER_PREAMBLE = f"""
    v_subject text := {_SUBJECT};
    v_previous text := current_setting('app.tenant_id', true);
    v_target text;
    v_old text[];
BEGIN
    IF v_subject IS NULL THEN
        RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
    END IF;
    PERFORM set_config('app.tenant_id', p_tenant::text, true);
    PERFORM 1 FROM tenants WHERE id = p_tenant AND status <> 'suspended' FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
    END IF;
    SELECT u.subject INTO v_target FROM users u WHERE u.id = p_user_id;
    SELECT array_agg(role ORDER BY role) INTO v_old FROM memberships
    WHERE tenant_id = p_tenant AND subject = v_target;
    IF v_target IS NULL OR v_old IS NULL THEN
        RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
    END IF;
"""

_LAST_ADMINISTRATOR_CHECK = """
    IF NOT EXISTS (
        SELECT 1 FROM memberships WHERE tenant_id = p_tenant AND role = 'administrator'
    ) THEN
        RAISE EXCEPTION 'last administrator' USING ERRCODE = 'QA002';
    END IF;
"""

_IS_ADMINISTRATOR = (
    "EXISTS (SELECT 1 FROM memberships WHERE tenant_id = p_tenant AND subject = v_subject "
    "AND role = 'administrator')"
)

_CHANGE_MEMBER_ROLES = f"""
CREATE FUNCTION change_member_roles(p_tenant uuid, p_user_id uuid, p_roles text[])
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
{_MEMBER_PREAMBLE}
    IF NOT {_IS_ADMINISTRATOR} THEN
        RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
    END IF;
    IF p_roles IS NULL OR cardinality(p_roles) < 1
       OR NOT (p_roles <@ ARRAY[{_PEOPLE_ROLES}]::text[]) THEN
        RAISE EXCEPTION 'invalid roles' USING ERRCODE = '22023';
    END IF;
    DELETE FROM memberships
    WHERE tenant_id = p_tenant AND subject = v_target AND NOT (role = ANY (p_roles));
    INSERT INTO memberships (id, tenant_id, subject, role)
    SELECT gen_random_uuid(), p_tenant, v_target, role FROM unnest(p_roles) AS role
    ON CONFLICT (tenant_id, subject, role) DO NOTHING;
{_LAST_ADMINISTRATOR_CHECK}
    INSERT INTO admin_events (id, tenant_id, actor_subject, action, target, details)
    VALUES (gen_random_uuid(), p_tenant, v_subject, 'member_roles_changed', p_user_id::text,
            jsonb_build_object('old', v_old,
                               'new', (SELECT array_agg(DISTINCT r ORDER BY r)
                                       FROM unnest(p_roles) AS r)));
    PERFORM set_config('app.tenant_id', COALESCE(v_previous, ''), true);
END $$
"""

_REMOVE_MEMBER = f"""
CREATE FUNCTION remove_member(p_tenant uuid, p_user_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
{_MEMBER_PREAMBLE}
    -- Administrators may remove anyone; everyone may leave (Q22).
    IF v_target <> v_subject AND NOT {_IS_ADMINISTRATOR} THEN
        RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
    END IF;
    DELETE FROM memberships WHERE tenant_id = p_tenant AND subject = v_target;
{_LAST_ADMINISTRATOR_CHECK}
    -- A removed person no longer receives approval requests on their linked phones.
    UPDATE channel_bindings SET revoked_at = now()
    WHERE tenant_id = p_tenant AND subject = v_target AND revoked_at IS NULL;
    INSERT INTO admin_events (id, tenant_id, actor_subject, action, target, details)
    VALUES (gen_random_uuid(), p_tenant, v_subject, 'member_removed', p_user_id::text,
            jsonb_build_object('old', v_old));
    PERFORM set_config('app.tenant_id', COALESCE(v_previous, ''), true);
END $$
"""


def _functions() -> None:
    for sql in (_CREATE_BUSINESS, _ACCEPT_INVITATION, _CHANGE_MEMBER_ROLES, _REMOVE_MEMBER):
        op.execute(sql)
    for signature in _FUNCTIONS:
        op.execute(f"ALTER FUNCTION {signature} OWNER TO quotation_owner")
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO quotation_app")


def downgrade() -> None:
    for signature in _FUNCTIONS:
        op.execute(f"DROP FUNCTION {signature}")

    op.drop_table("rate_limit_counters")
    for name in ("session_for_subject_select", "session_for_subject_update"):
        op.execute(f"DROP POLICY {name} ON user_sessions")

    op.execute("ALTER TABLE jobs NO FORCE ROW LEVEL SECURITY")
    op.execute("DELETE FROM jobs WHERE kind = 'send_account_email'")
    op.execute("ALTER TABLE jobs FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY account_email_jobs ON jobs")
    op.drop_constraint("ck_jobs_tenant", "jobs", type_="check")
    op.alter_column("jobs", "tenant_id", nullable=False)

    op.execute("REVOKE INSERT ON connection_events FROM quotation_app")
    op.execute("REVOKE INSERT, UPDATE ON connections FROM quotation_app")
    op.execute("REVOKE INSERT, UPDATE ON api_keys FROM quotation_app")
    op.drop_column("api_keys", "revoked_by")
    op.drop_column("api_keys", "created_by")

    for table in (
        "admin_events",
        "invitations",
        "account_notices",
        "password_resets",
        "email_verifications",
        "user_credentials",
    ):
        op.drop_table(table)

    # Businesses whose pricing was never completed could not price before either.
    op.execute("ALTER TABLE tenant_pricing_policies NO FORCE ROW LEVEL SECURITY")
    op.execute(
        "DELETE FROM tenant_pricing_policies WHERE currency IS NULL OR minor_units IS NULL "
        "OR rounding_mode IS NULL OR tax_rate IS NULL OR max_price_age_seconds IS NULL "
        "OR max_stock_age_seconds IS NULL"
    )
    op.execute("ALTER TABLE tenant_pricing_policies FORCE ROW LEVEL SECURITY")
    op.execute("REVOKE UPDATE ON tenant_pricing_policies FROM quotation_app")
    op.drop_column("tenant_pricing_policies", "updated_by")
    for column in (
        "currency",
        "minor_units",
        "rounding_mode",
        "tax_rate",
        "max_price_age_seconds",
        "max_stock_age_seconds",
    ):
        op.alter_column("tenant_pricing_policies", column, nullable=False)

    op.drop_table("tenant_profiles")  # logo files stay on disk under tenants/<t>/profile/

    op.execute("REVOKE UPDATE ON tenants FROM quotation_app")
    op.execute("DROP TRIGGER tenants_status_guard ON tenants")
    op.execute("DROP FUNCTION guard_tenant_status()")
    op.drop_constraint("ck_tenants_country", "tenants", type_="check")
    op.drop_constraint("ck_tenants_status", "tenants", type_="check")
    for column in ("updated_at", "went_live_at", "created_by", "time_zone", "country", "status"):
        op.drop_column("tenants", column)

    op.drop_constraint("fk_memberships_subject_users", "memberships", type_="foreignkey")
    op.drop_table("users")
