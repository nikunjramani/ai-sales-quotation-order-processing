import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Task } from "@/features/quotations/model/types";
import { DecisionPanel } from "@/features/quotations/ui/components/DecisionPanel";

import { jsonResponse, renderWithProviders } from "../../../../support/renderWithProviders";

const TASK: Task = {
  task_id: "task-1",
  version: 2,
  content_sha256: "a".repeat(64),
  status: "pending",
  created_at: "2026-10-22T10:00:00Z",
  decided_at: null,
};

function bodies(fetch: ReturnType<typeof vi.fn>) {
  return fetch.mock.calls.map(([, init]) => JSON.parse(String((init as RequestInit).body)));
}

describe("DecisionPanel", () => {
  it("sends the exact version hash and reuses the command ID when retrying", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(503, { detail: "down" }))
      .mockResolvedValueOnce(jsonResponse(200, { replayed: false }));
    vi.stubGlobal("fetch", fetch);
    const { client } = renderWithProviders(<DecisionPanel task={TASK} />);
    const refresh = vi.spyOn(client, "invalidateQueries");

    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect((await screen.findByRole("alert")).textContent).toContain("down");
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));

    const [first, second] = bodies(fetch);
    expect(first.content_sha256).toBe(TASK.content_sha256);
    expect(first.action).toBe("approve");
    expect(second.command_id).toBe(first.command_id);
    expect(fetch.mock.calls[0]?.[0]).toBe("/api/v1/tenants/t1/approval-tasks/task-1/decision");
    // The tenant's quotation lists and details are refreshed after the decision.
    await waitFor(() =>
      expect(refresh).toHaveBeenCalledWith({ queryKey: ["tenants", "t1", "quotations"] }),
    );
  });

  it("requires a reason before rejecting and sends nothing", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<DecisionPanel task={TASK} />);
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(screen.getByRole("alert").textContent).toContain("reason");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("explains a conflict and refreshes instead of retrying", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { detail: { message: "Already decided" } })),
    );
    const { client } = renderWithProviders(<DecisionPanel task={TASK} />);
    const refresh = vi.spyOn(client, "invalidateQueries");
    await userEvent.type(screen.getByLabelText(/Reason/), "Out of stock");
    await userEvent.click(screen.getByRole("button", { name: "Ask for changes" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Already decided");
    expect(refresh).toHaveBeenCalled();
  });
});
