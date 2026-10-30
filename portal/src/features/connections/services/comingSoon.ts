// Tools that are planned but not built yet (ADR 0025 addendum, user decision 2026-10-30).
// The Integrations screen shows them greyed out with "Coming soon" and no button. This is the
// only list to edit: once a provider with the same key is installed on the server, its real
// card appears instead and this entry is ignored automatically.

export interface ComingSoonTool {
  /** The provider key the real package will use (matches AvailableTool.provider_key). */
  provider_key: string;
  name: string;
  description: string;
}

export const COMING_SOON: readonly ComingSoonTool[] = [
  {
    provider_key: "whatsapp",
    name: "WhatsApp",
    description: "Chat with customers and send quotes on WhatsApp.",
  },
  {
    provider_key: "email",
    name: "Email",
    description: "Receive requests and send quotes by email.",
  },
  {
    provider_key: "sms",
    name: "SMS",
    description: "Text messages for order updates.",
  },
];
