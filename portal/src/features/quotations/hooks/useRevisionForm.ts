import { useRef, useState, type FormEvent } from "react";

import { isApiError } from "@/shared/api/httpClient";
import { newCommandId } from "@/shared/lib/commandId";

import type { EditableLine, PricingIssue, QuotationDetail } from "../model/types";
import {
  cleanLines,
  emptyLine,
  initialRevisionLines,
  pricingIssuesFrom,
  revisionProblem,
} from "../services/quotationService";
import { useReviseQuotation } from "./useQuotations";

/** State and behaviour of the revision form: edit lines, submit, show pricing issues. */
export function useRevisionForm(detail: QuotationDetail) {
  const revise = useReviseQuotation();
  const [lines, setLines] = useState<EditableLine[]>(() => initialRevisionLines(detail));
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [issues, setIssues] = useState<PricingIssue[]>([]);
  const commandId = useRef(newCommandId());

  function updateLine(index: number, field: keyof EditableLine, value: string) {
    setLines((previous) =>
      previous.map((line, position) => (position === index ? { ...line, [field]: value } : line)),
    );
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = revisionProblem(lines, reason);
    setProblem(invalid);
    setIssues([]);
    if (invalid) return;
    revise.mutate(
      {
        quotationId: detail.summary.quotation_id,
        request: {
          command_id: commandId.current,
          base_version: detail.summary.current_version,
          lines: cleanLines(lines),
          reason: reason.trim(),
        },
      },
      {
        onSuccess: () => {
          commandId.current = newCommandId();
        },
        onError: (error) => {
          // Rejected input was not stored, so the next attempt is a new command.
          if (isApiError(error, 422)) {
            commandId.current = newCommandId();
            setIssues(pricingIssuesFrom(error.detail));
          }
          setProblem(error.message);
        },
      },
    );
  }

  return {
    lines,
    updateLine,
    addLine: () => setLines((previous) => [...previous, emptyLine()]),
    removeLine: (index: number) =>
      setLines((previous) => previous.filter((_, position) => position !== index)),
    reason,
    setReason,
    submit,
    busy: revise.isPending,
    error: problem,
    issues,
  };
}
