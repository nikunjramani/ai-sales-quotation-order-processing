import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { useCurrentTenant } from "@/features/tenant";
import { dateTime } from "@/shared/lib/format";
import { QueryState } from "@/shared/ui/QueryState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

import { useContact, useContacts, useMergeContact } from "../../hooks/useConversations";
import type { Contact } from "../../model/types";
import { consentLabel } from "../../services/conversationService";

export function ContactDetailPage() {
  const { contactId = "" } = useParams();
  const found = useContact(contactId);
  const { can } = useCurrentTenant();
  const data = found.data;
  return (
    <section>
      <p>
        <Link to="/contacts">← Contacts</Link>
      </p>
      <QueryState isLoading={found.isLoading} error={found.error}>
        {data && (
          <>
            <h1>{data.contact.name ?? "Unknown"}</h1>
            <p className="muted small">
              {details(data.contact)}
              {" · "}claimed details are not verified
            </p>
            <h2>Addresses on our tools</h2>
            <ul className="list">
              {data.identities.map((identity) => (
                <li key={identity.identity_id} className="row static">
                  <span>
                    {identity.connection_name}
                    <br />
                    <span className="muted small">{consentLabel(identity.consent)}</span>
                  </span>
                </li>
              ))}
            </ul>
            <h2>Conversations</h2>
            <ul className="list">
              {data.conversations.map((id) => (
                <li key={id}>
                  <Link className="row" to={`/inbox/${id}`}>
                    Open conversation
                  </Link>
                </li>
              ))}
            </ul>
            <h2>Enquiries</h2>
            <ul className="list">
              {data.enquiries.map((enquiry) => (
                <li key={enquiry.enquiry_id} className="row static">
                  <span>
                    {dateTime(enquiry.received_at)}{" "}
                    {enquiry.quotation_id && (
                      <Link to={`/quotations/${enquiry.quotation_id}`}>Quotation</Link>
                    )}
                  </span>
                  <StatusBadge status={enquiry.quotation_status ?? enquiry.status} />
                </li>
              ))}
            </ul>
            {can("contacts:merge") && (
              <MergeBox contact={data.contact} suggestions={data.suggestions} />
            )}
          </>
        )}
      </QueryState>
    </section>
  );
}

function details(contact: Contact): string {
  return [contact.company, contact.email, contact.phone].filter(Boolean).join(" · ") || "No details";
}

/** D13: never automatic; suggestions only for the same verified email/phone; no undo. */
function MergeBox({ contact, suggestions }: { contact: Contact; suggestions: Contact[] }) {
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState<Contact | null>(null);
  const candidates = useContacts(query);
  const merge = useMergeContact(contact.contact_id);
  const navigate = useNavigate();
  const options = [
    ...suggestions,
    ...(query ? (candidates.data ?? []) : []).filter(
      (item) => item.contact_id !== contact.contact_id,
    ),
  ];
  return (
    <section className="card">
      <h2>Merge into another contact</h2>
      {suggestions.length > 0 && (
        <p className="small">Suggested: the same verified email or phone.</p>
      )}
      <input
        type="search"
        placeholder="Find the contact to keep"
        value={query}
        maxLength={100}
        onChange={(event) => setQuery(event.target.value)}
      />
      <ul className="list">
        {options.map((item) => (
          <li key={item.contact_id}>
            <button className="secondary" onClick={() => setChosen(item)}>
              {item.name ?? "Unknown"} · {details(item)}
            </button>
          </li>
        ))}
      </ul>
      {chosen && (
        <div className="card">
          <p>
            Keep <strong>{chosen.name ?? "Unknown"}</strong> ({details(chosen)}) and move
            everything of <strong>{contact.name ?? "Unknown"}</strong> ({details(contact)}) into it.
            This cannot be undone.
          </p>
          <button
            disabled={merge.isPending}
            onClick={() =>
              merge.mutate(chosen.contact_id, {
                onSuccess: () => navigate(`/contacts/${chosen.contact_id}`),
              })
            }
          >
            Merge
          </button>{" "}
          <button className="secondary" onClick={() => setChosen(null)}>
            Cancel
          </button>
          {merge.error && <p className="error">{merge.error.message}</p>}
        </div>
      )}
    </section>
  );
}
