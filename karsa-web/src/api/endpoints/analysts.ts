import { ApiClient } from "../client";
import { ListAnalystsResponseDTO } from "../../types/analysts/list-analysts-response.dto";

export const AnalystsApi = {
  listMetrics: (): Promise<ListAnalystsResponseDTO> => {
    return ApiClient.fetch<ListAnalystsResponseDTO>("/workers/metrics");
  }
};
