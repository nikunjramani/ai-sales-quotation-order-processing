import { Navigate, useNavigate } from "react-router";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useLoginForm } from "../hooks/useLoginForm";
import { useSession } from "../hooks/useSession";

export function LoginPage() {
  const navigate = useNavigate();
  const session = useSession();
  const form = useLoginForm(() => navigate("/quotations", { replace: true }));

  if (session.data) return <Navigate to="/quotations" replace />;
  if (form.provider === "disabled") {
    return (
      <main className="narrow">
        <h1>Quotation Portal</h1>
        <p className="notice">Sign-in is not configured on this server.</p>
      </main>
    );
  }

  return (
    <main className="narrow">
      <h1>Quotation Portal</h1>
      <form className="card" onSubmit={form.submit}>
        <p className="notice">
          Development sign-in: choose a synthetic demo person. No password is asked, so this is
          disabled in production; a real identity provider (OIDC) replaces it later.
        </p>
        <label htmlFor="subject">Person</label>
        <select id="subject" value={form.subject} onChange={(event) => form.setSubject(event.target.value)}>
          {form.subjects.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <ErrorMessage message={form.error} />
        <button type="submit" disabled={form.busy || !form.subject}>
          Sign in
        </button>
      </form>
    </main>
  );
}
