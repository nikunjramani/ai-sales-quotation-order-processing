import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { isApiError } from "@/shared/api/httpClient";

import { accountRepository } from "../api/accountRepository";
import { passwordHints, PROBLEM_TEXT, problemsFrom } from "../services/passwordRules";

/** Sign-up form. The answer is the same for new and existing addresses (Q7). */
export function useSignupForm() {
  const signup = useMutation({ mutationFn: accountRepository.signup });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const hints = password ? passwordHints(password, email).map((p) => PROBLEM_TEXT[p]) : [];

  function submit(event: FormEvent) {
    event.preventDefault();
    signup.mutate({ email, password, display_name: displayName || undefined });
  }

  let errors: string[] = [];
  if (signup.error) {
    if (isApiError(signup.error, 422)) {
      const problems = problemsFrom(signup.error.detail);
      errors = problems.length ? problems : [signup.error.message];
    } else if (isApiError(signup.error, 429)) {
      errors = ["Too many sign-ups from here. Wait a while and try again."];
    } else {
      errors = ["Sign-up failed; try again."];
    }
  }

  return {
    email,
    setEmail,
    password,
    setPassword,
    displayName,
    setDisplayName,
    hints,
    submit,
    busy: signup.isPending,
    sent: signup.isSuccess,
    errors,
  };
}
