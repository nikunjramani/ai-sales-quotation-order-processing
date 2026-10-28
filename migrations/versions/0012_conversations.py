"""Customers and conversations, follow-up rounds and website chat (phase 4, ADR 0021).

- contacts: one customer of one business (name, company, claimed or verified email/phone).
  merged_into_id records a manual merge (D13: administrators and sales operators, no undo).
- contact_identities: one address of a contact on one connection (a chat visitor ID, an API
  customer_reference...), with its consent state (D15).
- conversations: one per identity. Its row lock serialises all messages of one customer on one
  tool, so a follow-up and a new message can never race.
- conversation_messages: append-only thread, inbound (an inbox event) and outbound (an outbox
  message). seq orders them and is the website chat's polling cursor.
- enquiries gain conversation_id / contact_id. The API role may now change an enquiry's status,
  but a trigger allows it only needs_clarification -> received (a follow-up reopening it).
- workflow_runs.round: each reading of an enquiry is one round with a fresh LangGraph thread;
  earlier rounds stay as history.
- customer_action_refs: one reference per (quotation version, identity) for Accept/Decline.
  Buttons use its ID with the sender checked; a secure link (Q1) carries a token whose SHA-256
  is stored. Deviation from the plan: one row per offer instead of one per action, so an offer
  is answered once whichever button is pressed.
- customer_sessions: website chat visitor sessions (only the secret's SHA-256 is stored).
- connections.public_handle: the chat link /chat/<handle> (Q13; changed at most once).
- tenants.acknowledge_enquiries: the "we are preparing your quotation" setting (D14, on).

Lookup policies reveal one row by a presented value (session ID, handle, token hash) before the
tenant is known, like api_key_lookup. Every new table has forced tenant RLS.

Backfill: one identity, contact and conversation per (API connection, customer_reference); one
inbound message per existing enquiry. Enquiries without a customer_reference get no contact (Q5).

Downgrade loses follow-up rounds (runs with round > 1 and their checkpoints), every follow-up
message's text (enquiries.text holds the first message only), contacts, sessions and action
references. Back up first.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_conversations"
down_revision = "0011_catalogue"
branch_labels = None
depends_on = None

_TENANT_FILTER = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_NOW = sa.text("now()")
_NEW_TABLES = (
    "contacts",
    "contact_identities",
    "conversations",
    "conversation_messages",
    "customer_action_refs",
    "customer_sessions",
)
# Owner-run backfill: FORCE RLS also binds the owner, so it is lifted and restored.
_BACKFILL_TABLES = (
    "enquiries",
    "inbox_events",
    "attachments",
    "contacts",
    "contact_identities",
    "conversations",
    "conversation_messages",
)
_CHECKPOINT_TABLES = ("checkpoint_writes", "checkpoint_blobs", "checkpoints")


def _created() -> sa.Column[Any]:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False)


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], name=f"fk_{table}_tenant_id_tenants"
    )


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("company", sa.String(200), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_into_id", sa.Uuid(), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_by", sa.String(200), nullable=True),
        _created(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_contacts"),
        _tenant_fk("contacts"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_contacts_tenant_id_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "merged_into_id"],
            ["contacts.tenant_id", "contacts.id"],
            name="fk_contacts_merged",
        ),
        sa.CheckConstraint(
            "merged_into_id IS NULL OR merged_into_id <> id", name="ck_contacts_not_self"
        ),
        sa.CheckConstraint(
            "(merged_into_id IS NULL) = (merged_at IS NULL)", name="ck_contacts_merged"
        ),
    )
    op.execute("CREATE INDEX ix_contacts_tenant_email ON contacts (tenant_id, lower(email))")
    op.create_index("ix_contacts_tenant_phone", "contacts", ["tenant_id", "phone"])

    op.create_table(
        "contact_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("connection_ref", sa.Uuid(), nullable=False),
        # A chat visitor ID, a phone number, an address, an API customer_reference...
        sa.Column("external_id", sa.String(320), nullable=False),
        sa.Column("display_hint", sa.String(200), nullable=True),  # never used for matching
        sa.Column("verified", sa.Boolean(), nullable=False),  # the tool proves the sender
        sa.Column(
            "consent_status", sa.String(16), server_default=sa.text("'implied'"), nullable=False
        ),
        sa.Column("consent_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_source", sa.String(100), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_contact_identities"),
        _tenant_fk("contact_identities"),
        sa.UniqueConstraint(
            "tenant_id", "connection_ref", "external_id", name="uq_contact_identities_external"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_contact_identities_tenant_id_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "contact_id"],
            ["contacts.tenant_id", "contacts.id"],
            name="fk_contact_identities_contact",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_ref"],
            ["connections.tenant_id", "connections.id"],
            name="fk_contact_identities_connection",
        ),
        sa.CheckConstraint(
            "consent_status IN ('implied', 'opted_in', 'opted_out')",
            name="ck_contact_identities_consent",
        ),
    )
    op.create_index(
        "ix_contact_identities_contact", "contact_identities", ["tenant_id", "contact_id"]
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("connection_ref", sa.Uuid(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        _tenant_fk("conversations"),
        sa.UniqueConstraint("tenant_id", "identity_id", name="uq_conversations_identity"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_conversations_tenant_id_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "contact_id"],
            ["contacts.tenant_id", "contacts.id"],
            name="fk_conversations_contact",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "identity_id"],
            ["contact_identities.tenant_id", "contact_identities.id"],
            name="fk_conversations_identity",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_ref"],
            ["connections.tenant_id", "connections.id"],
            name="fk_conversations_connection",
        ),
    )
    op.execute(
        "CREATE INDEX ix_conversations_inbox ON conversations (tenant_id, last_message_at DESC)"
    )
    op.create_index("ix_conversations_contact", "conversations", ["tenant_id", "contact_id"])

    op.add_column("enquiries", sa.Column("conversation_id", sa.Uuid(), nullable=True))
    op.add_column("enquiries", sa.Column("contact_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_enquiries_conversation",
        "enquiries",
        "conversations",
        ["tenant_id", "conversation_id"],
        ["tenant_id", "id"],
    )
    op.create_foreign_key(
        "fk_enquiries_contact",
        "enquiries",
        "contacts",
        ["tenant_id", "contact_id"],
        ["tenant_id", "id"],
    )
    op.create_index(
        "ix_enquiries_conversation_status", "enquiries", ["tenant_id", "conversation_id", "status"]
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("enquiry_id", sa.Uuid(), nullable=True),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("author", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("template_key", sa.String(64), nullable=True),
        sa.Column("inbox_event_id", sa.Uuid(), nullable=True),
        sa.Column("outbound_message_id", sa.Uuid(), nullable=True),
        sa.Column(
            "attachment_ids",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_conversation_messages"),
        _tenant_fk("conversation_messages"),
        sa.UniqueConstraint("inbox_event_id", name="uq_conversation_messages_inbox"),
        sa.UniqueConstraint("outbound_message_id", name="uq_conversation_messages_outbound"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.id"],
            name="fk_conversation_messages_conversation",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enquiry_id"],
            ["enquiries.tenant_id", "enquiries.id"],
            name="fk_conversation_messages_enquiry",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "inbox_event_id"],
            ["inbox_events.tenant_id", "inbox_events.id"],
            name="fk_conversation_messages_inbox_event",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "outbound_message_id"],
            ["outbound_messages.tenant_id", "outbound_messages.id"],
            name="fk_conversation_messages_outbound",
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')", name="ck_conversation_messages_direction"
        ),
        sa.CheckConstraint(
            "author IN ('customer', 'system', 'staff')", name="ck_conversation_messages_author"
        ),
        sa.CheckConstraint(
            "(direction = 'inbound' AND inbox_event_id IS NOT NULL "
            "AND outbound_message_id IS NULL) OR (direction = 'outbound' "
            "AND outbound_message_id IS NOT NULL AND inbox_event_id IS NULL)",
            name="ck_conversation_messages_source",
        ),
        sa.CheckConstraint(
            "conversation_id IS NOT NULL OR enquiry_id IS NOT NULL",
            name="ck_conversation_messages_owner",
        ),
        sa.CheckConstraint("length(text) <= 20000", name="ck_conversation_messages_text"),
    )
    op.create_index(
        "ix_conversation_messages_conversation",
        "conversation_messages",
        ["tenant_id", "conversation_id", "seq"],
    )
    op.create_index(
        "ix_conversation_messages_enquiry",
        "conversation_messages",
        ["tenant_id", "enquiry_id", "seq"],
    )

    op.add_column(
        "workflow_runs",
        sa.Column("round", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_check_constraint("ck_workflow_runs_round", "workflow_runs", "round >= 1")
    op.drop_constraint("uq_workflow_runs_enquiry_version", "workflow_runs", type_="unique")
    op.create_unique_constraint(
        "uq_workflow_runs_enquiry_round",
        "workflow_runs",
        ["tenant_id", "enquiry_id", "graph_version", "round"],
    )

    op.create_table(
        "customer_action_refs",
        sa.Column("id", sa.Uuid(), nullable=False),  # the button reference (sender checked)
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("outbound_message_id", sa.Uuid(), nullable=True),
        sa.Column("token_sha256", sa.String(64), nullable=True),  # secure link only (Q1)
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_id", sa.Uuid(), nullable=True),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_customer_action_refs"),
        _tenant_fk("customer_action_refs"),
        sa.UniqueConstraint("token_sha256", name="uq_customer_action_refs_token"),
        sa.UniqueConstraint(
            "tenant_id",
            "quotation_id",
            "version",
            "identity_id",
            name="uq_customer_action_refs_offer",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "quotation_id", "version"],
            [
                "quotation_versions.tenant_id",
                "quotation_versions.quotation_id",
                "quotation_versions.version",
            ],
            name="fk_customer_action_refs_version",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "identity_id"],
            ["contact_identities.tenant_id", "contact_identities.id"],
            name="fk_customer_action_refs_identity",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.id"],
            name="fk_customer_action_refs_conversation",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"], ["quotation_responses.id"], name="fk_customer_action_refs_response"
        ),
        sa.CheckConstraint(
            "(consumed_at IS NULL) = (response_id IS NULL)", name="ck_customer_action_refs_consumed"
        ),
    )

    op.create_table(
        "customer_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_ref", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("secret_sha256", sa.String(64), nullable=False),
        sa.Column("ip_hmac", sa.String(64), nullable=False),  # never the address itself
        sa.Column("origin", sa.String(200), nullable=True),
        _created(),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_customer_sessions"),
        _tenant_fk("customer_sessions"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connection_ref"],
            ["connections.tenant_id", "connections.id"],
            name="fk_customer_sessions_connection",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "identity_id"],
            ["contact_identities.tenant_id", "contact_identities.id"],
            name="fk_customer_sessions_identity",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.id"],
            name="fk_customer_sessions_conversation",
        ),
    )
    op.create_index(
        "ix_customer_sessions_connection", "customer_sessions", ["tenant_id", "connection_ref"]
    )

    op.add_column("connections", sa.Column("public_handle", sa.String(64), nullable=True))
    op.add_column(
        "connections",
        sa.Column("public_handle_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_connections_public_handle", "connections", ["public_handle"])
    op.create_check_constraint(
        "ck_connections_public_handle",
        "connections",
        "public_handle IS NULL OR public_handle ~ '^[a-z0-9](?:[a-z0-9-]{1,62}[a-z0-9])$'",
    )
    op.add_column(
        "tenants",
        sa.Column(
            "acknowledge_enquiries", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )

    for table in _NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_FILTER}) WITH CHECK ({_TENANT_FILTER})"
        )
    # Before the tenant is known, each reveals only the one row whose key was presented.
    op.execute(
        "CREATE POLICY customer_session_lookup ON customer_sessions FOR SELECT TO quotation_app "
        "USING (id = NULLIF(current_setting('app.customer_session_id', true), '')::uuid)"
    )
    op.execute(
        "CREATE POLICY connection_handle_lookup ON connections FOR SELECT TO quotation_app "
        "USING (public_handle = NULLIF(current_setting('app.public_handle', true), ''))"
    )
    op.execute(
        "CREATE POLICY customer_action_lookup ON customer_action_refs FOR SELECT "
        "TO quotation_app USING (token_sha256 = "
        "NULLIF(current_setting('app.action_token_sha256', true), ''))"
    )
    op.execute(
        "CREATE TRIGGER conversation_messages_immutable BEFORE UPDATE OR DELETE "
        "ON conversation_messages FOR EACH ROW EXECUTE FUNCTION reject_change()"
    )
    op.execute(
        """
        CREATE FUNCTION guard_enquiry_reopen() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user = 'quotation_app' AND NEW.status IS DISTINCT FROM OLD.status
               AND NOT (OLD.status = 'needs_clarification' AND NEW.status = 'received') THEN
                RAISE EXCEPTION 'enquiry status change not allowed for this role'
                    USING ERRCODE = '42501';
            END IF;
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER enquiries_reopen_guard BEFORE UPDATE OF status ON enquiries "
        "FOR EACH ROW EXECUTE FUNCTION guard_enquiry_reopen()"
    )

    # Both roles route customer messages (the API and website chat in the request, webhook
    # providers in the worker), so both write the conversation tables.
    for role in ("quotation_app", "quotation_worker"):
        op.execute(f"GRANT SELECT, INSERT ON contacts, conversation_messages TO {role}")
        op.execute(
            "GRANT SELECT, INSERT, UPDATE (contact_id, last_seen_at, consent_status, "
            f"consent_changed_at, consent_source) ON contact_identities TO {role}"
        )
        op.execute(
            "GRANT SELECT, INSERT, UPDATE (contact_id, last_message_at, last_inbound_at) "
            f"ON conversations TO {role}"
        )
    op.execute(
        "GRANT UPDATE (merged_into_id, merged_at, merged_by, updated_at) ON contacts "
        "TO quotation_app"
    )
    op.execute("GRANT UPDATE (status, updated_at, contact_id) ON enquiries TO quotation_app")
    op.execute(
        "GRANT SELECT, UPDATE (consumed_at, response_id) ON customer_action_refs TO quotation_app"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (token_sha256, outbound_message_id) "
        "ON customer_action_refs TO quotation_worker"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (last_seen_at, expires_at, revoked_at) "
        "ON customer_sessions TO quotation_app"
    )
    op.execute("GRANT SELECT ON customer_sessions TO quotation_worker")
    op.execute("GRANT UPDATE (acknowledge_enquiries) ON tenants TO quotation_app")
    op.execute(
        "GRANT UPDATE (public_handle, public_handle_changed_at) ON connections TO quotation_app"
    )

    for table in _BACKFILL_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    _backfill()
    for table in _BACKFILL_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _backfill() -> None:
    # 1-3: one identity, contact and conversation per (connection, customer_reference). The API
    # key proves the caller and the reference is the caller's own label, so it is "verified".
    op.execute(
        """
        CREATE TEMPORARY TABLE _identities ON COMMIT DROP AS
        SELECT e.tenant_id, i.connection_ref, e.customer_reference AS external_id,
               gen_random_uuid() AS identity_id, gen_random_uuid() AS contact_id,
               gen_random_uuid() AS conversation_id,
               min(e.received_at) AS first_seen, max(e.received_at) AS last_seen
        FROM enquiries e
        JOIN inbox_events i ON i.tenant_id = e.tenant_id AND i.id = e.inbox_event_id
        WHERE e.customer_reference IS NOT NULL AND btrim(e.customer_reference) <> ''
        GROUP BY e.tenant_id, i.connection_ref, e.customer_reference
        """
    )
    op.execute(
        """
        INSERT INTO contacts (id, tenant_id, display_name, created_at, updated_at)
        SELECT contact_id, tenant_id, left(external_id, 200), first_seen, last_seen
        FROM _identities
        """
    )
    op.execute(
        """
        INSERT INTO contact_identities (id, tenant_id, contact_id, connection_ref, external_id,
                                        verified, first_seen_at, last_seen_at)
        SELECT identity_id, tenant_id, contact_id, connection_ref, external_id, true,
               first_seen, last_seen
        FROM _identities
        """
    )
    op.execute(
        """
        INSERT INTO conversations (id, tenant_id, contact_id, identity_id, connection_ref,
                                   last_message_at, last_inbound_at, created_at)
        SELECT conversation_id, tenant_id, contact_id, identity_id, connection_ref,
               last_seen, last_seen, first_seen
        FROM _identities
        """
    )
    # 4: link the enquiries (the reopen trigger only restricts the API role).
    op.execute(
        """
        UPDATE enquiries e SET conversation_id = d.conversation_id, contact_id = d.contact_id
        FROM inbox_events i, _identities d
        WHERE i.tenant_id = e.tenant_id AND i.id = e.inbox_event_id
          AND d.tenant_id = e.tenant_id AND d.connection_ref = i.connection_ref
          AND d.external_id = e.customer_reference
        """
    )
    # 5-6: one inbound message per enquiry, in time order so seq follows time. Enquiries
    # without a reference keep conversation_id NULL and are never continued (Q5).
    op.execute(
        """
        INSERT INTO conversation_messages (id, tenant_id, conversation_id, enquiry_id, direction,
                                           author, text, inbox_event_id, attachment_ids, at)
        SELECT gen_random_uuid(), e.tenant_id, e.conversation_id, e.id, 'inbound', 'customer',
               e.text, e.inbox_event_id,
               COALESCE((SELECT jsonb_agg(a.id::text ORDER BY a.created_at, a.id)
                         FROM attachments a
                         WHERE a.tenant_id = e.tenant_id AND a.enquiry_id = e.id), '[]'::jsonb),
               e.received_at
        FROM enquiries e
        ORDER BY e.received_at, e.id
        """
    )
    # 9: every enquiry must now have its first message.
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM enquiries e WHERE NOT EXISTS (
                SELECT 1 FROM conversation_messages m
                WHERE m.tenant_id = e.tenant_id AND m.enquiry_id = e.id)) THEN
                RAISE EXCEPTION 'backfill left an enquiry without a message';
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    # Follow-up rounds and their checkpoints only have meaning in this version.
    op.execute("ALTER TABLE workflow_runs NO FORCE ROW LEVEL SECURITY")
    for table in _CHECKPOINT_TABLES:
        op.execute(
            f"DELETE FROM {table} WHERE thread_id IN "
            "(SELECT id::text FROM workflow_runs WHERE round > 1)"
        )
    op.execute("DELETE FROM workflow_runs WHERE round > 1")
    op.execute("ALTER TABLE workflow_runs FORCE ROW LEVEL SECURITY")
    op.drop_constraint("uq_workflow_runs_enquiry_round", "workflow_runs", type_="unique")
    op.create_unique_constraint(
        "uq_workflow_runs_enquiry_version",
        "workflow_runs",
        ["tenant_id", "enquiry_id", "graph_version"],
    )
    op.drop_constraint("ck_workflow_runs_round", "workflow_runs", type_="check")
    op.drop_column("workflow_runs", "round")

    op.execute("DROP TRIGGER enquiries_reopen_guard ON enquiries")
    op.execute("DROP FUNCTION guard_enquiry_reopen()")
    op.execute("REVOKE UPDATE (status, updated_at, contact_id) ON enquiries FROM quotation_app")
    op.execute(
        "REVOKE UPDATE (public_handle, public_handle_changed_at) ON connections FROM quotation_app"
    )
    op.execute("REVOKE UPDATE (acknowledge_enquiries) ON tenants FROM quotation_app")
    op.execute("DROP POLICY connection_handle_lookup ON connections")

    op.drop_column("tenants", "acknowledge_enquiries")
    op.drop_constraint("ck_connections_public_handle", "connections", type_="check")
    op.drop_constraint("uq_connections_public_handle", "connections", type_="unique")
    op.drop_column("connections", "public_handle_changed_at")
    op.drop_column("connections", "public_handle")

    op.drop_table("customer_sessions")
    op.drop_table("customer_action_refs")
    op.execute("DROP TRIGGER conversation_messages_immutable ON conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_enquiries_conversation_status", table_name="enquiries")
    op.drop_constraint("fk_enquiries_contact", "enquiries", type_="foreignkey")
    op.drop_constraint("fk_enquiries_conversation", "enquiries", type_="foreignkey")
    op.drop_column("enquiries", "contact_id")
    op.drop_column("enquiries", "conversation_id")
    op.drop_table("conversations")
    op.drop_table("contact_identities")
    op.drop_table("contacts")
