import { type FormEvent, useState } from "react";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useOnceValues, useOneClick } from "../../hooks/useConnections";
import type { Connection, PendingAction } from "../../model/types";
import { formDefaults, formFields, stepTexts } from "../../services/connectionService";

/**
 * The one step a business still has to do for a tool (phase 5). Four kinds, all generic:
 * show_steps (numbered steps in the tool itself, with a one-time code), open_url (a provider
 * page, e.g. a login), provider_page (a setup page our API serves for the package) and
 * fill_form (a form from the package's JSON schema). The list reloads every 5 seconds while
 * a tool is being set up, so the panel disappears when the tool confirms.
 */
export function PendingActionPanel({ connection }: { connection: Connection }) {
  const action = connection.pending;
  if (!action) return null;
  return (
    <div className="notice">
      <strong>{action.title}</strong>
      {action.kind === "show_steps" && <ShowSteps connection={connection} action={action} />}
      {action.kind === "open_url" && action.url && (
        <OpenPage href={action.url} label="Open the page" />
      )}
      {action.kind === "provider_page" && <ProviderPage connection={connection} action={action} />}
      {action.kind === "fill_form" && <FillForm connection={connection} action={action} />}
      {action.expires_at && (
        <p className="muted small">
          Valid until {new Date(action.expires_at).toLocaleString()}. Press Enable again for a new
          one.
        </p>
      )}
    </div>
  );
}

function ShowSteps({ connection, action }: { connection: Connection; action: PendingAction }) {
  const remembered = useOnceValues(connection.connection_id);
  const once = Object.keys(action.once).length > 0 ? action.once : (remembered ?? {});
  const steps = stepTexts(action, once);
  return (
    <>
      <ol>
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      {Object.entries(once).map(([name, value]) => (
        <p key={name}>
          Your {name}: <code>{value}</code>{" "}
          <button onClick={() => void navigator.clipboard?.writeText(value)}>Copy</button>
        </p>
      ))}
    </>
  );
}

function OpenPage({ href, label }: { href: string; label: string }) {
  return (
    <p>
      <a className="button primary" href={href} target="_blank" rel="noopener noreferrer">
        {label}
      </a>{" "}
      <span className="muted small">This page updates when the tool confirms.</span>
    </p>
  );
}

function ProviderPage({ connection, action }: { connection: Connection; action: PendingAction }) {
  const actions = useOneClick();
  return (
    <OpenPage href={actions.pageUrl(connection.connection_id, action.action_id)} label="Continue" />
  );
}

function FillForm({ connection, action }: { connection: Connection; action: PendingAction }) {
  const actions = useOneClick();
  const fields = formFields(action.form_schema);
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    formDefaults(action.form_schema),
  );
  const submit = (event: FormEvent) => {
    event.preventDefault();
    actions.resume.mutate({
      connectionId: connection.connection_id,
      actionId: action.action_id,
      submission: values,
    });
  };
  return (
    <form onSubmit={submit}>
      {fields.map((field) => (
        <label key={field.name}>
          {field.label}
          {field.input === "select" ? (
            <select
              required={field.required}
              value={String(values[field.name] ?? "")}
              onChange={(event) => setValues({ ...values, [field.name]: event.target.value })}
            >
              <option value="">Choose…</option>
              {field.options.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          ) : field.input === "checkbox" ? (
            <input
              type="checkbox"
              checked={Boolean(values[field.name])}
              onChange={(event) => setValues({ ...values, [field.name]: event.target.checked })}
            />
          ) : (
            <input
              type={field.input}
              required={field.required}
              autoComplete={field.input === "password" ? "new-password" : undefined}
              value={String(values[field.name] ?? "")}
              onChange={(event) =>
                setValues({
                  ...values,
                  [field.name]:
                    field.input === "number" ? Number(event.target.value) : event.target.value,
                })
              }
            />
          )}
          {field.help && <span className="muted small">{field.help}</span>}
        </label>
      ))}
      <button className="primary" type="submit" disabled={actions.resume.isPending}>
        Send
      </button>
      <ErrorMessage message={actions.resume.error?.message} />
    </form>
  );
}
