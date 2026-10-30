import { LeaveBusinessCard } from "@/features/business";
import { LinkedAccountsSection } from "@/features/connections";
import { useCurrentTenant } from "@/features/tenant";
import { ErrorMessage } from "@/shared/ui/QueryState";

import { useChangePasswordForm, useProfileForm } from "../../hooks/useProfile";
import { PasswordField } from "../components/PasswordField";
import { VerifyEmailBanner } from "../components/VerifyEmailBanner";

export function ProfilePage() {
  const profile = useProfileForm();
  const password = useChangePasswordForm();
  if (!profile.user) {
    return (
      <section>
        <h1>Your profile</h1>
        <p className="muted">Demo people signed in with the development sign-in have no profile.</p>
        <ManagerAccounts />
      </section>
    );
  }
  return (
    <section>
      <h1>Your profile</h1>
      <VerifyEmailBanner />
      <ManagerAccounts />
      <form className="card" onSubmit={profile.submit}>
        <p className="muted small">Email: {profile.user.email} (cannot be changed yet)</p>
        <label htmlFor="profile-name">Name</label>
        <input
          id="profile-name"
          maxLength={100}
          value={profile.name}
          onChange={(event) => profile.setName(event.target.value)}
        />
        <ErrorMessage message={profile.error} />
        {profile.saved && <p className="muted small">Saved.</p>}
        <button type="submit" disabled={profile.busy}>
          Save
        </button>
      </form>
      <h2>Change password</h2>
      <form className="card" onSubmit={password.submit}>
        <PasswordField
          label="Current password"
          value={password.current}
          onChange={password.setCurrent}
          autoComplete="current-password"
        />
        <PasswordField
          label="New password"
          value={password.next}
          onChange={password.setNext}
          autoComplete="new-password"
          hints={password.hints}
        />
        {password.errors.map((error) => (
          <p key={error} role="alert" className="error">
            {error}
          </p>
        ))}
        {password.done && (
          <p className="muted small">Password changed; your other sessions were signed out.</p>
        )}
        <button type="submit" disabled={password.busy}>
          Change password
        </button>
      </form>
      <h2>Business</h2>
      <LeaveBusinessCard />
    </section>
  );
}

/** Managers link their own phone or chat account here (moved from "Apps & channels", ADR 0025). */
function ManagerAccounts() {
  const { tenant, can } = useCurrentTenant();
  if (!tenant || !can("quotations:approve")) return null;
  return <LinkedAccountsSection />;
}
