import { useState, type FormEvent } from "react";

import { isApiError } from "@/shared/api/httpClient";

import { useAuthConfig, useLogin } from "./useSession";

/** Everything the login page needs; the page itself only renders. */
export function useLoginForm(onSignedIn: () => void) {
  const config = useAuthConfig();
  const login = useLogin();
  const [chosen, setChosen] = useState<string | null>(null);
  const subject = chosen ?? config.data?.dev_subjects[0] ?? "";

  function submit(event: FormEvent) {
    event.preventDefault();
    login.mutate(subject, { onSuccess: onSignedIn });
  }

  let error: string | null = null;
  if (config.error) error = "Cannot reach the API. Is it running?";
  else if (login.error) {
    error = isApiError(login.error, 401)
      ? "Sign-in failed: this person is not a member of any business."
      : "Sign-in failed; try again.";
  }

  return {
    provider: config.data?.provider,
    subjects: config.data?.dev_subjects ?? [],
    subject,
    setSubject: setChosen,
    submit,
    busy: login.isPending,
    error,
  };
}
