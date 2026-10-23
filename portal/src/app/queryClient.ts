import { QueryClient } from "@tanstack/react-query";

import { isApiError } from "@/shared/api/httpClient";

// One cache for all server state. Client mistakes (4xx) are not retried; network or server
// errors are retried twice. Mutations (decisions, revisions) are never retried automatically:
// a person retries them, reusing the same command ID.
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        refetchOnWindowFocus: true,
        retry: (failureCount, error) =>
          !(isApiError(error) && error.status < 500) && failureCount < 2,
      },
      mutations: { retry: false },
    },
  });
}
