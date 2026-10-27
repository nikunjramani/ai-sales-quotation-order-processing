import type { RouteObject } from "react-router";

import { AcceptInvitationPage } from "./ui/pages/AcceptInvitationPage";
import { ForgotPasswordPage } from "./ui/pages/ForgotPasswordPage";
import { LoginPage } from "./ui/pages/LoginPage";
import { ProfilePage } from "./ui/pages/ProfilePage";
import { ResetPasswordPage } from "./ui/pages/ResetPasswordPage";
import { SignupPage } from "./ui/pages/SignupPage";
import { VerifyEmailPage } from "./ui/pages/VerifyEmailPage";

/** Screens without a session (the email links open some of them). */
export const accountPublicRoutes: RouteObject[] = [
  { path: "login", element: <LoginPage /> },
  { path: "signup", element: <SignupPage /> },
  { path: "verify-email", element: <VerifyEmailPage /> },
  { path: "forgot-password", element: <ForgotPasswordPage /> },
  { path: "reset-password", element: <ResetPasswordPage /> },
  { path: "invitations/accept", element: <AcceptInvitationPage /> },
];

/** Screens for a signed-in person, with or without a business. */
export const accountRoutes: RouteObject[] = [{ path: "profile", element: <ProfilePage /> }];
