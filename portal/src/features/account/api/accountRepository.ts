import type { Session, SessionUser } from "@/features/auth";
import { http, setCsrfToken } from "@/shared/api/httpClient";

import type {
  ChangePasswordInput,
  InvitationPreview,
  LoginInput,
  ResetInput,
  SignupInput,
} from "../model/types";

async function signedIn(promise: Promise<Session>): Promise<Session> {
  const session = await promise;
  setCsrfToken(session.csrf_token);
  return session;
}

// Repository: HTTP calls for accounts. Tokens from email links go in request bodies only.
export const accountRepository = {
  signup: (input: SignupInput) =>
    http<{ status: string }>("/auth/signup", { method: "POST", body: input }),

  verifyEmail: (token: string) =>
    http<{ status: string }>("/auth/verify-email", { method: "POST", body: { token } }),

  resendVerification: () =>
    http<{ status: string }>("/auth/verify-email/resend", { method: "POST" }),

  login: (input: LoginInput) =>
    signedIn(http<Session>("/auth/login", { method: "POST", body: input })),

  /** Development only: sign in as a seeded demo person without a password. */
  devLogin: (subject: string) =>
    signedIn(http<Session>("/auth/dev-login", { method: "POST", body: { subject } })),

  forgotPassword: (email: string) =>
    http<{ status: string }>("/auth/password/forgot", { method: "POST", body: { email } }),

  resetPassword: (input: ResetInput) =>
    http<void>("/auth/password/reset", { method: "POST", body: input }),

  changePassword: (input: ChangePasswordInput) =>
    http<void>("/auth/password/change", { method: "POST", body: input }),

  updateProfile: (display_name: string) =>
    http<SessionUser>("/account/profile", { method: "PATCH", body: { display_name } }),

  previewInvitation: (token: string) =>
    http<InvitationPreview>("/invitations/preview", { method: "POST", body: { token } }),

  acceptInvitation: (token: string) =>
    http<{ tenant_id: string }>("/invitations/accept", { method: "POST", body: { token } }),
};
