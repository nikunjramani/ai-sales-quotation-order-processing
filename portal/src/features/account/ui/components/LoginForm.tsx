import { Link } from "react-router";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useLoginForm } from "../../hooks/useSignIn";
import { PasswordField } from "./PasswordField";

/** Email + password (D1), plus the development sign-in when the server offers it. */
export function LoginForm({ onSignedIn }: { onSignedIn: () => void }) {
  const form = useLoginForm(onSignedIn);
  return (
    <>
      <form className="card" onSubmit={form.submit}>
        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={(event) => form.setEmail(event.target.value)}
        />
        <PasswordField
          label="Password"
          value={form.password}
          onChange={form.setPassword}
          autoComplete="current-password"
        />
        <ErrorMessage message={form.error} />
        <button type="submit" disabled={form.busy}>
          Sign in
        </button>
        <p className="small">
          <Link to="/forgot-password">Forgot your password?</Link> ·{" "}
          <Link to="/signup">Create an account</Link>
        </p>
      </form>
      {form.devLogin && (
        <form className="card" onSubmit={form.submitDev}>
          <p className="notice">
            Development sign-in: choose a seeded demo person, no password. The server refuses
            this in production.
          </p>
          <label htmlFor="dev-subject">Demo person</label>
          <select
            id="dev-subject"
            value={form.subject}
            onChange={(event) => form.setSubject(event.target.value)}
          >
            {form.subjects.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <ErrorMessage message={form.devError} />
          <button type="submit" className="secondary" disabled={form.devBusy || !form.subject}>
            Sign in as demo person
          </button>
        </form>
      )}
    </>
  );
}
