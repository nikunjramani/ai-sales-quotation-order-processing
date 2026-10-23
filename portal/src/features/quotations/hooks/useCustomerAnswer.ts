import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { useTenantId } from "@/features/tenant";
import { isApiError } from "@/shared/api/httpClient";
import { newCommandId } from "@/shared/lib/commandId";

import { quotationRepository } from "../api/quotationRepository";
import { withdrawalProblem } from "../services/customerService";
import { quotationKeys } from "./queryKeys";

/** What the customer holds (status, validity) and every answer recorded so far. */
export function useCustomerView(quotationId: string) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: quotationKeys.customer(tenantId, quotationId),
    queryFn: () => quotationRepository.customerView(tenantId, quotationId),
  });
}

/**
 * Withdraw an issued quotation with a reason. One command ID is kept until it succeeds, so a
 * retry after a network error cannot record a second withdrawal.
 */
export function useWithdrawForm(quotationId: string) {
  const tenantId = useTenantId();
  const client = useQueryClient();
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const command = useRef<string | null>(null);
  const withdraw = useMutation({
    mutationFn: (request: { command_id: string; reason: string }) =>
      quotationRepository.withdraw(tenantId, quotationId, request),
    onSettled: () => client.invalidateQueries({ queryKey: quotationKeys.all(tenantId) }),
  });

  function submit() {
    const invalid = withdrawalProblem(reason);
    setProblem(invalid);
    if (invalid) return;
    command.current ??= newCommandId();
    withdraw.mutate(
      { command_id: command.current, reason: reason.trim() },
      {
        onSuccess: () => {
          command.current = null;
        },
        onError: (error) => {
          // 409: the customer answered (or it closed) meanwhile; the page refreshes itself.
          setProblem(
            isApiError(error, 409) ? `${error.message}. The page has been refreshed.` : error.message,
          );
        },
      },
    );
  }

  return { reason, setReason, submit, busy: withdraw.isPending, error: problem };
}
