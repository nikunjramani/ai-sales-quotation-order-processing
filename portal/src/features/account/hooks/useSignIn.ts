import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { useAuthConfig, useSessionCache } from "@/features/auth";
import { isApiError } from "@/shared/api/httpClient";

import { accountRepository } from "../api/accountRepository";

export function usePasswordLogin() {
  const cache = useSessionCache();
  return useMutation({ mutationFn: accountRepository.login, onSuccess: cache.set });
}

export function useDevLogin() {
  const cache = useSessionCache();
  return useMutation({ mutationFn: accountRepository.devLogin, onSuccess: cache.set });
}

function loginError(error: Error | null): string | null {
  if (!error) return null;
  if (isApiError(error, 401)) return "Email or password is incorrect.";
  if (isApiError(error, 429)) return "Too many attempts. Wait a few minutes and try again.";
  return "Sign-in failed; try again.";
}

/** Everything the login page needs; the page itself only renders. */
export function useLoginForm(onSignedIn: () => void) {
  const config = useAuthConfig();
  const login = usePasswordLogin();
  const dev = useDevLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [chosen, setChosen] = useState<string | null>(null);
  const subject = chosen ?? config.data?.dev_subjects[0] ?? "";

  function submit(event: FormEvent) {
    event.preventDefault();
    login.mutate({ email, password }, { onSuccess: onSignedIn });
  }

  function submitDev(event: FormEvent) {
    event.preventDefault();
    dev.mutate(subject, { onSuccess: onSignedIn });
  }

  return {
    email,
    setEmail,
    password,
    setPassword,
    submit,
    busy: login.isPending,
    error: config.error ? "Cannot reach the API. Is it running?" : loginError(login.error),
    devLogin: config.data?.dev_login ?? false,
    subjects: config.data?.dev_subjects ?? [],
    subject,
    setSubject: setChosen,
    submitDev,
    devBusy: dev.isPending,
    devError: dev.error ? "Development sign-in failed." : null,
  };
}
