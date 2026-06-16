import { ApiClient } from "../client";
import { PerformanceRequestDTO } from "../../types/performance/performance-request.dto";
import { PerformanceResponseDTO } from "../../types/performance/performance-response.dto";
import { buildQueryString } from "../utils/query-string";

export const PerformanceApi = {
  getAttribution: (params: PerformanceRequestDTO): Promise<PerformanceResponseDTO> => {
    return ApiClient.fetch<PerformanceResponseDTO>(`/performance/attribution${buildQueryString(params)}`);
  }
};
