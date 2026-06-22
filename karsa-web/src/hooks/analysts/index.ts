import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { AnalystsApi } from "../../api/endpoints/analysts";
import { mapListAnalysts } from "../../features/analysts/utils/mappers";
import { ListAnalystsVM } from "../../features/analysts/types/viewmodels";

export function useAnalystsMetrics() {
  return useQuery<ListAnalystsVM, ApiError>({
    queryKey: queryKeys.analysts.metrics(),
    queryFn: async () => {
      const response = await fetch('/workers/metrics');
      if (!response.ok) throw new Error('Failed to fetch analysts');
      const data = await response.json();
      return mapListAnalysts(data);
    },
    staleTime: 60 * 1000,
  });
}
