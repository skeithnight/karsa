import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 1000 * 60, // 60s default
      gcTime: 1000 * 60 * 5, // 5m default
      refetchOnWindowFocus: false,
    },
  },
});
