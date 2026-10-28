import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router";

import { useSessionCache } from "@/features/auth";
import { isApiError } from "@/shared/api/httpClient";

import { accountRepository } from "../api/accountRepository";
import { INVALID_LINK } from "../services/links";
import { tokenFromSearch } from "../services/links";
import { PROBLEM_TEXT, passwordHints, problemsFrom } from "../services/passwordRules";

/**
 * The token of the email link that opened this page, read once. It is then removed from the
 * address bar, so it is not kept in the browser history or shown over someone's shoulder.
 */
export function useLinkToken(): string | null {
  const location = useLocation();
  const navigate = useNavigate();
  const [token] = useState(() => tokenFromSearch(location.search));
  useEffect(() => {
    if (location.search) navigate(location.pathname, { replace: true });
  }, [location.pathname, location.search, navigate]);
  return token;
}

/** Verifies the email address once when the page opens. */
export function useVerifyEmail(token: string | null) {
  const cache = useSessionCache();
  const verify = useMutation({
    mutationFn: accountRepository.verifyEmail,
    onSuccess: () => void cache.refresh(),
  });
  const started = useRef(false);
  useEffect(() => {
    if (token && !started.current) {
      started.current = true;
      verify.mutate(token);
    }
  }, [token, verify]);
  return {
    done: verify.isSuccess,
    busy: verify.isPending,
    error: !token || verify.isError ? INVALID_LINK : null,
  };
}

export function useResendVerification() {
  const resend = useMutation({ mutationFn: accountRepository.resendVerification });
  return {
    resend: () => resend.mutate(),
    sent: resend.isSuccess,
    busy: resend.isPending,
    error: isApiError(resend.error, 429)
      ? "Please wait a minute before asking again."
      : resend.error
        ? "Could not send the email; try again."
        : null,
  };
}

export function useForgotPasswordForm() {
  const forgot = useMutation({ mutationFn: accountRepository.forgotPassword });
  const [email, setEmail] = useState("");
  return {
    email,
    setEmail,
    submit(event: FormEvent) {
      event.preventDefault();
      forgot.mutate(email);
    },
    busy: forgot.isPending,
    sent: forgot.isSuccess,
    error: isApiError(forgot.error, 429)
      ? "Too many requests. Wait a while and try again."
      : forgot.error
        ? "Something went wrong; try again."
        : null,
  };
}

export function useResetPasswordForm(token: string | null) {
  const reset = useMutation({ mutationFn: accountRepository.resetPassword });
  const [password, setPassword] = useState("");
  let errors: string[] = [];
  if (!token || isApiError(reset.error, 400)) errors = [INVALID_LINK];
  else if (isApiError(reset.error, 422)) errors = problemsFrom(reset.error?.detail);
  else if (reset.error) errors = ["Something went wrong; try again."];
  return {
    password,
    setPassword,
    hints: password ? passwordHints(password, "").map((p) => PROBLEM_TEXT[p]) : [],
    submit(event: FormEvent) {
      event.preventDefault();
      if (token) reset.mutate({ token, new_password: password });
    },
    busy: reset.isPending,
    done: reset.isSuccess,
    errors,
  };
}
