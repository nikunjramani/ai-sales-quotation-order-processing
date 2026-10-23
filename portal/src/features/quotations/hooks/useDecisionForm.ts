import { useRef, useState } from "react";

import { isApiError } from "@/shared/api/httpClient";
import { newCommandId } from "@/shared/lib/commandId";

import type { ApprovalAction, Task } from "../model/types";
import { decisionProblem } from "../services/quotationService";
import { useDecideQuotation } from "./useQuotations";

/**
 * State and behaviour of the decision panel.
 *
 * The request carries the content hash the manager saw, so a decision never applies to content
 * that changed meanwhile. One command ID is kept per action until it succeeds, so retrying after
 * a network error can never record a second decision.
 */
export function useDecisionForm(task: Task) {
  const decide = useDecideQuotation();
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const commands = useRef(new Map<ApprovalAction, string>());

  function submit(action: ApprovalAction) {
    const invalid = decisionProblem(action, reason);
    setProblem(invalid);
    if (invalid) return;
    const commandId = commands.current.get(action) ?? newCommandId();
    commands.current.set(action, commandId);
    decide.mutate(
      {
        taskId: task.task_id,
        request: {
          command_id: commandId,
          action,
          content_sha256: task.content_sha256,
          reason: reason.trim() || null,
        },
      },
      {
        onSuccess: () => commands.current.clear(),
        onError: (error) => {
          // 409: someone already decided or the version changed; the page refreshes itself.
          setProblem(isApiError(error, 409) ? `${error.message}. The page has been refreshed.` : error.message);
        },
      },
    );
  }

  return { reason, setReason, submit, busy: decide.isPending, error: problem };
}
