import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { PerformanceApi } from "../../api/endpoints/performance";
import { mapPerformanceAttribution } from "../../features/performance/utils/mappers";
import { PerformanceAttributionVM } from "../../features/performance/types/viewmodels";
import { PerformanceRequestDTO } from "../../types/performance/performance-request.dto";

export function usePerformanceAttribution(params: PerformanceRequestDTO) {
  return useQuery<PerformanceAttributionVM, ApiError>({
    queryKey: queryKeys.performance.attribution(params),
    queryFn: async () => {
      const response = await PerformanceApi.getAttribution(params);
      return mapPerformanceAttribution(response);
    },
    staleTime: 5 * 60 * 1000,
  });
}
