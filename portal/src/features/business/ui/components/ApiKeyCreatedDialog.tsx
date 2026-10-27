import type { NewApiKey } from "../../model/types";

/**
 * Shows a new API key once. It cannot be shown again: the server keeps only a hash of it. The
 * token is only in this component's props, which disappear when the dialog closes.
 */
export function ApiKeyCreatedDialog({ apiKey, onClose }: { apiKey: NewApiKey; onClose: () => void }) {
  return (
    <div className="card warn" role="dialog" aria-label="New API key">
      <p>
        <strong>Copy this key now.</strong> It is shown only once; store it in your website's or
        system's secret settings.
      </p>
      <p>
        <code>{apiKey.token}</code>
      </p>
      <p className="muted small">
        Send enquiries to <code>POST /api/v1/enquiries</code> with the header{" "}
        <code>Authorization: Bearer &lt;key&gt;</code>. Each key sees only its own enquiries.
      </p>
      <button className="primary" onClick={onClose}>
        I have stored it
      </button>
    </div>
  );
}
