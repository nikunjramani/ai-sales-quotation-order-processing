import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { useSession, useSessionCache } from "@/features/auth";
import { isApiError } from "@/shared/api/httpClient";

import { accountRepository } from "../api/accountRepository";
import { PROBLEM_TEXT, passwordHints, problemsFrom } from "../services/passwordRules";

/** Display name (Q23: name and password only; the email cannot be changed yet). */
export function useProfileForm() {
  const session = useSession();
  const cache = useSessionCache();
  const user = session.data?.user ?? null;
  const [name, setName] = useState<string | null>(null);
  const update = useMutation({
    mutationFn: accountRepository.updateProfile,
    onSuccess: () => void cache.refresh(),
  });
  return {
    user,
    name: name ?? user?.display_name ?? "",
    setName,
    submit(event: FormEvent) {
      event.preventDefault();
      update.mutate(name ?? user?.display_name ?? "");
    },
    busy: update.isPending,
    saved: update.isSuccess,
    error: update.error ? update.error.message : null,
  };
}

/** Your other sessions are signed out; this one stays. */
export function useChangePasswordForm() {
  const session = useSession();
  const change = useMutation({ mutationFn: accountRepository.changePassword });
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const email = session.data?.user?.email ?? "";
  let errors: string[] = [];
  if (isApiError(change.error, 400)) errors = ["The current password is incorrect."];
  else if (isApiError(change.error, 422)) errors = problemsFrom(change.error?.detail);
  else if (isApiError(change.error, 429)) errors = ["Too many attempts; wait a few minutes."];
  else if (change.error) errors = ["Something went wrong; try again."];
  return {
    current,
    setCurrent,
    next,
    setNext,
    hints: next ? passwordHints(next, email).map((p) => PROBLEM_TEXT[p]) : [],
    submit(event: FormEvent) {
      event.preventDefault();
      change.mutate(
        { current_password: current, new_password: next },
        {
          onSuccess: () => {
            setCurrent("");
            setNext("");
          },
        },
      );
    },
    busy: change.isPending,
    done: change.isSuccess,
    errors,
  };
}
