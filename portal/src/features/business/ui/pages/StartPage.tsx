import { Hand } from "lucide-react";
import { Link, Navigate } from "react-router";

import { useSession } from "@/features/auth";
import { PageHeader } from "@/shared/ui/PageHeader";

/** For a signed-in person without a business: create one, or join through an invitation. */
export function StartPage() {
  const session = useSession();
  if (session.data && session.data.tenants.length > 0) return <Navigate to="/" replace />;
  const verified = session.data?.user?.email_verified ?? false;
  return (
    <section>
      <PageHeader icon={Hand} title="Welcome!" hint="Let's get you set up. It only takes a few minutes." />
      <div className="card">
        <h2>Create your business</h2>
        <p>Set up your business, invite colleagues and connect your website. Nothing is sent to
          customers until you press Go live.</p>
        {verified ? (
          <Link className="button primary" to="/businesses/new">
            Create a business
          </Link>
        ) : (
          <p className="muted">Confirm your email address first (see the message above).</p>
        )}
      </div>
      <div className="card">
        <h2>Joining a colleague's business?</h2>
        <p>Open the invitation link from your email.</p>
      </div>
    </section>
  );
}
