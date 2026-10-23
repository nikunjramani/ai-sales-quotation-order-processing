import type { ReactNode } from "react";

interface Props {
  isLoading: boolean;
  error: Error | null;
  isEmpty?: boolean;
  emptyText?: string;
  children: ReactNode;
}

/** Shows loading, error and empty states consistently; renders children once data is ready. */
export function QueryState({ isLoading, error, isEmpty, emptyText = "Nothing here.", children }: Props) {
  if (error) return <ErrorMessage message={error.message} />;
  if (isLoading) return <p className="muted">Loading…</p>;
  if (isEmpty) return <p className="muted">{emptyText}</p>;
  return <>{children}</>;
}

export function ErrorMessage({ message }: { message: string | null | undefined }) {
  return message ? (
    <p role="alert" className="error">
      {message}
    </p>
  ) : null;
}
