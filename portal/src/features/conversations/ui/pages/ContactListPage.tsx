import { useState } from "react";
import { Link } from "react-router";

import { dateTime } from "@/shared/lib/format";
import { QueryState } from "@/shared/ui/QueryState";

import { useContacts } from "../../hooks/useConversations";

export function ContactListPage() {
  const [query, setQuery] = useState("");
  const contacts = useContacts(query);
  return (
    <section>
      <h1>Contacts</h1>
      <input
        type="search"
        placeholder="Search name, email, phone, company"
        value={query}
        maxLength={100}
        onChange={(event) => setQuery(event.target.value)}
      />
      <QueryState
        isLoading={contacts.isLoading}
        error={contacts.error}
        isEmpty={contacts.data?.length === 0}
      >
        <ul className="list">
          {contacts.data?.map((contact) => (
            <li key={contact.contact_id}>
              <Link className="row" to={`/contacts/${contact.contact_id}`}>
                <span>
                  <strong>{contact.name ?? "Unknown"}</strong>
                  {contact.company && <span className="muted"> · {contact.company}</span>}
                  <br />
                  <span className="muted small">
                    {[contact.email, contact.phone].filter(Boolean).join(" · ") || "No details"}
                    {contact.last_activity && ` · ${dateTime(contact.last_activity)}`}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}
