import { Link } from "react-router";

import { useSignupForm } from "../../hooks/useSignup";
import { CHECK_EMAIL } from "../../services/links";
import { PasswordField } from "../components/PasswordField";

export function SignupPage() {
  const form = useSignupForm();
  if (form.sent) {
    return (
      <main className="narrow">
        <h1>Check your email</h1>
        <p className="card">{CHECK_EMAIL}</p>
        <p>
          <Link to="/login">Sign in</Link>
        </p>
      </main>
    );
  }
  return (
    <main className="narrow">
      <h1>Create an account</h1>
      <form className="card" onSubmit={form.submit}>
        <label htmlFor="signup-email">Email</label>
        <input
          id="signup-email"
          type="email"
          autoComplete="email"
          required
          maxLength={254}
          value={form.email}
          onChange={(event) => form.setEmail(event.target.value)}
        />
        <label htmlFor="signup-name">Your name (optional)</label>
        <input
          id="signup-name"
          autoComplete="name"
          maxLength={100}
          value={form.displayName}
          onChange={(event) => form.setDisplayName(event.target.value)}
        />
        <PasswordField
          label="Password"
          value={form.password}
          onChange={form.setPassword}
          autoComplete="new-password"
          hints={form.hints}
        />
        {form.errors.map((error) => (
          <p key={error} role="alert" className="error">
            {error}
          </p>
        ))}
        <button type="submit" disabled={form.busy}>
          Create account
        </button>
        <p className="small">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </main>
  );
}
