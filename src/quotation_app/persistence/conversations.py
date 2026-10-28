"""Conversation rows inside a caller's transaction (phase 4).

Lock order, everywhere: the conversation row first, then its enquiries. A message from a
customer locks its conversation before looking at the open enquiries; the worker, when it
records an outcome that sends something, locks the conversation before the enquiry too. So the
API and the worker never wait for each other in opposite orders (no deadlock).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Connection, exists, func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from quotation_app.domain.conversations import BEING_READ, Author, Direction, OpenEnquiry
from quotation_app.domain.intake import EnquiryStatus
from quotation_app.persistence.models import (
    Contact,
    ContactIdentity,
    Conversation,
    ConversationMessage,
    Enquiry,
    Quotation,
    WorkflowRun,
)

MAX_DISPLAY_NAME = 200
_ROUTABLE = [status.value for status in (*BEING_READ, EnquiryStatus.NEEDS_CLARIFICATION)]
EXTRACTION_GRAPHS = "enquiry-extraction-%"


@dataclass(frozen=True)
class ConversationRef:
    conversation_id: UUID
    contact_id: UUID
    identity_id: UUID


def ensure_conversation(
    connection: Connection,
    tenant_id: UUID,
    connection_ref: UUID,
    external_id: str,
    verified: bool,
    display_name: str | None,
    at: datetime,
) -> ConversationRef:
    """Find or create the identity, its contact and its conversation, and lock the conversation.

    An advisory lock on (connection, sender) makes two first messages of a new customer wait
    for each other, so exactly one contact is created.
    """
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"identity:{tenant_id}:{connection_ref}:{external_id}"},
    )
    identity = connection.execute(
        select(ContactIdentity.id, ContactIdentity.contact_id).where(
            ContactIdentity.tenant_id == tenant_id,
            ContactIdentity.connection_ref == connection_ref,
            ContactIdentity.external_id == external_id,
        )
    ).one_or_none()
    if identity is None:
        contact_id, identity_id = uuid4(), uuid4()
        connection.execute(
            insert(Contact).values(
                id=contact_id,
                tenant_id=tenant_id,
                display_name=(display_name or external_id)[:MAX_DISPLAY_NAME],
            )
        )
        connection.execute(
            insert(ContactIdentity).values(
                id=identity_id,
                tenant_id=tenant_id,
                contact_id=contact_id,
                connection_ref=connection_ref,
                external_id=external_id,
                verified=verified,
                first_seen_at=at,
                last_seen_at=at,
            )
        )
    else:
        identity_id, contact_id = identity.id, identity.contact_id
        connection.execute(
            update(ContactIdentity)
            .where(ContactIdentity.tenant_id == tenant_id, ContactIdentity.id == identity_id)
            .values(last_seen_at=func.greatest(ContactIdentity.last_seen_at, at))
        )
    connection.execute(
        insert(Conversation)
        .values(
            id=uuid4(),
            tenant_id=tenant_id,
            contact_id=contact_id,
            identity_id=identity_id,
            connection_ref=connection_ref,
            last_message_at=at,
        )
        .on_conflict_do_nothing(index_elements=["tenant_id", "identity_id"])
    )
    conversation_id: UUID = connection.execute(
        select(Conversation.id)
        .where(Conversation.tenant_id == tenant_id, Conversation.identity_id == identity_id)
        .with_for_update()
    ).scalar_one()
    return ConversationRef(conversation_id, contact_id, identity_id)


def open_enquiries(
    connection: Connection, tenant_id: UUID, conversation_id: UUID
) -> list[tuple[OpenEnquiry, UUID]]:
    """Enquiries a message could continue, locked, each with its correlation ID."""
    asked = (
        select(func.max(WorkflowRun.updated_at))
        .where(
            WorkflowRun.tenant_id == Enquiry.tenant_id,
            WorkflowRun.enquiry_id == Enquiry.id,
            WorkflowRun.graph_version.like(EXTRACTION_GRAPHS),
            WorkflowRun.status == EnquiryStatus.NEEDS_CLARIFICATION.value,
        )
        .scalar_subquery()
    )
    quoted = exists().where(
        Quotation.tenant_id == Enquiry.tenant_id, Quotation.enquiry_id == Enquiry.id
    )
    rows = connection.execute(
        select(
            Enquiry.id,
            Enquiry.status,
            Enquiry.received_at,
            Enquiry.correlation_id,
            asked.label("asked_at"),
            quoted.label("quoted"),
        )
        .where(
            Enquiry.tenant_id == tenant_id,
            Enquiry.conversation_id == conversation_id,
            Enquiry.status.in_(_ROUTABLE),
        )
        .order_by(Enquiry.received_at)
        .with_for_update(of=Enquiry)
    ).all()
    return [
        (
            OpenEnquiry(
                row.id, EnquiryStatus(row.status), row.received_at, row.asked_at, row.quoted
            ),
            row.correlation_id,
        )
        for row in rows
    ]


def lock_conversation_of(connection: Connection, tenant_id: UUID, enquiry_id: UUID) -> None:
    """Worker side of the lock order: the enquiry's conversation first (if it has one)."""
    conversation_id = connection.execute(
        select(Enquiry.conversation_id).where(
            Enquiry.tenant_id == tenant_id, Enquiry.id == enquiry_id
        )
    ).scalar_one_or_none()
    if conversation_id is not None:
        connection.execute(
            select(Conversation.id)
            .where(Conversation.tenant_id == tenant_id, Conversation.id == conversation_id)
            .with_for_update()
        )


def append_inbound(
    connection: Connection,
    tenant_id: UUID,
    conversation_id: UUID | None,
    enquiry_id: UUID,
    inbox_event_id: UUID,
    body: str,
    attachment_ids: Sequence[UUID],
    at: datetime,
) -> None:
    connection.execute(
        insert(ConversationMessage).values(
            id=uuid4(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            enquiry_id=enquiry_id,
            direction=Direction.INBOUND.value,
            author=Author.CUSTOMER.value,
            text=body,
            inbox_event_id=inbox_event_id,
            attachment_ids=[str(item) for item in attachment_ids],
            at=at,
        )
    )
    if conversation_id is not None:
        connection.execute(
            update(Conversation)
            .where(Conversation.tenant_id == tenant_id, Conversation.id == conversation_id)
            .values(
                last_message_at=func.greatest(Conversation.last_message_at, at),
                last_inbound_at=func.greatest(func.coalesce(Conversation.last_inbound_at, at), at),
            )
        )
