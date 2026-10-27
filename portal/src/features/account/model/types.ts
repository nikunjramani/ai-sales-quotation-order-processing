export interface SignupInput {
  email: string;
  password: string;
  display_name?: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface ResetInput {
  token: string;
  new_password: string;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

/** What an invitation link shows before accepting (only a hint of the invited address). */
export interface InvitationPreview {
  business_name: string;
  roles: string[];
  email_hint: string;
  expires_at: string;
}

/** Reasons the server gives for refusing a password (same rules as the form's hints). */
export type PasswordProblem = "too_short" | "too_long" | "too_common" | "contains_email";
