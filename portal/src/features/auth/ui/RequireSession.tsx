import type { ReactNode } from "react";
import { Navigate } from "react-router";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useSession } from "../hooks/useSession";

/** Route guard: renders its children only for a signed-in person, otherwise goes to /login. */
export function RequireSession({ children }: { children: ReactNode }) {
  const session = useSession();
  if (session.isLoading) return <p className="muted center">Loading…</p>;
  if (session.error) return <ErrorMessage message={session.error.message} />;
  if (!session.data) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
