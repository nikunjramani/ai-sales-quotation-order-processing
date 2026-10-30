// Service: pure rules for showing connections. No React, no HTTP. The screens decide by
// purposes and status, never by provider name, so a new tool needs no portal change.

import type {
  AvailableTool,
  Connection,
  ConnectionStatus,
  JsonSchema,
  PendingAction,
  Purpose,
} from "../model/types";

export const PURPOSE_LABEL: Record<Purpose, string> = {
  customer_messages: "Customer messages",
  manager_approvals: "Manager approvals",
  catalogue: "Product data",
  payments: "Payments",
  orders: "Orders",
};

export const STATUS_VIEW: Record<
  ConnectionStatus,
  { label: string; tone: "good" | "bad" | "warn" | "info" }
> = {
  setting_up: { label: "Setting up", tone: "info" },
  active: { label: "Active", tone: "good" },
  error: { label: "Needs attention", tone: "bad" },
  disabled: { label: "Disabled", tone: "warn" },
};

/** A manager can link their own account only on an active connection used for approvals. */
export function canLink(connection: Connection): boolean {
  return (
    connection.status === "active" &&
    connection.purposes.includes("manager_approvals")
  );
}

export function purposeText(connection: Connection): string {
  return connection.purposes
    .map((purpose) => PURPOSE_LABEL[purpose] ?? purpose)
    .join(", ");
}

/** "https://a.example\n\n https://b.example " -> ["https://a.example", "https://b.example"]. */
export function originsFromText(text: string): string[] {
  return text
    .split(/\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

/** Phase 5: a tool that may cost money needs the "may incur costs" tick before Enable. */
export function needsCostTick(tool: AvailableTool): boolean {
  return !tool.free;
}

/** One-click tools not enabled yet (an existing one shows its own step or status instead). */
export function enablable(tools: AvailableTool[], connections: Connection[]): AvailableTool[] {
  return tools.filter(
    (tool) =>
      tool.kind === "one_click" &&
      !connections.some(
        (item) => item.provider_key === tool.provider_key && item.status !== "disabled",
      ),
  );
}

/** While a tool is being set up, the list is asked again every 5 seconds. */
export function pollInterval(connections: Connection[] | undefined): number | false {
  return connections?.some((item) => item.status === "setting_up") ? 5000 : false;
}

const MISSING = "(press Enable again for a new one)";

/** Steps with the one-time values this browser still knows (from the Enable answer). */
export function stepTexts(action: PendingAction, once: Record<string, string>): string[] {
  const value = Object.values(once)[0];
  if (value === undefined) return action.steps;
  return action.steps.map((step) => step.split(MISSING).join(value));
}

export interface FormField {
  name: string;
  label: string;
  input: "text" | "number" | "checkbox" | "password" | "select";
  required: boolean;
  help: string | null;
  options: string[];
}

/** Fields of a setup form's JSON schema. Secret fields are write-only password inputs. */
export function formFields(schema: JsonSchema | null): FormField[] {
  const required = new Set(schema?.required ?? []);
  return Object.entries(schema?.properties ?? {}).map(([name, field]) => {
    let input: FormField["input"] = "text";
    if (field.enum?.length) input = "select";
    else if (field.type === "boolean") input = "checkbox";
    else if (field.type === "number" || field.type === "integer") input = "number";
    else if (field.writeOnly || field.format === "password") input = "password";
    return {
      name,
      label: field.title ?? name,
      input,
      required: required.has(name),
      help: field.description ?? null,
      options: field.enum ?? [],
    };
  });
}

/** A form's starting values: each field's schema default (never for secret fields). */
export function formDefaults(schema: JsonSchema | null): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const [name, field] of Object.entries(schema?.properties ?? {})) {
    if (field.default !== undefined && !field.writeOnly && field.format !== "password") {
      values[name] = field.default;
    }
  }
  return values;
}

/** Disabling a tool needs its name typed exactly (it stops its messages at once). */
export function disableConfirmed(typed: string, connection: Connection): boolean {
  return typed.trim() === connection.display_name;
}

/** One card per kind of tool (e.g. all API keys together), for the Integrations screen. */
export interface ToolGroup {
  providerKey: string;
  providerName: string;
  purposes: Purpose[];
  /** Working, being set up or needing attention: shown in the card. */
  current: Connection[];
  /** Switched off: hidden behind "Show switched off (n)". */
  switchedOff: Connection[];
  needsAttention: number;
}

/** Groups by provider, in first-seen order; a group with only switched-off rows still shows. */
export function groupConnections(connections: Connection[]): ToolGroup[] {
  const groups = new Map<string, ToolGroup>();
  for (const connection of connections) {
    let group = groups.get(connection.provider_key);
    if (!group) {
      group = {
        providerKey: connection.provider_key,
        providerName: connection.provider_name,
        purposes: [],
        current: [],
        switchedOff: [],
        needsAttention: 0,
      };
      groups.set(connection.provider_key, group);
    }
    for (const purpose of connection.purposes) {
      if (!group.purposes.includes(purpose)) group.purposes.push(purpose);
    }
    if (connection.status === "disabled") group.switchedOff.push(connection);
    else group.current.push(connection);
    if (connection.status === "error") group.needsAttention += 1;
  }
  return [...groups.values()];
}

/** "3 active" / "2 active, 1 needs attention" / "Switched off". */
export function groupSummary(group: ToolGroup): string {
  if (group.current.length === 0) return "Switched off";
  const working = group.current.length - group.needsAttention;
  const parts = [`${working} active`];
  if (group.needsAttention) parts.push(`${group.needsAttention} needs attention`);
  return parts.join(", ");
}

/** Planned tools whose real provider is not installed and not connected yet. */
export function comingSoon<T extends { provider_key: string }>(
  planned: readonly T[],
  available: AvailableTool[],
  connections: Connection[],
): T[] {
  const known = new Set([
    ...available.map((tool) => tool.provider_key),
    ...connections.map((item) => item.provider_key),
  ]);
  return planned.filter((tool) => !known.has(tool.provider_key));
}
