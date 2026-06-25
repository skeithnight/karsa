import { ApiClient } from "../client";
import { PerformanceRequestDTO } from "../../types/performance/performance-request.dto";
import { PerformanceResponseDTO } from "../../types/performance/performance-response.dto";
import { buildQueryString } from "../utils/query-string";

/** Brier score timeseries entry from the API */
export interface BrierScoreDTO {
  evaluation_sequence: number;
  score: number;
  algorithm_version: string;
  recorded_at: string;
  capability_version_id: string | null;
}

/** Brinson attribution row from the API */
export interface BrinsonAttributionDTO {
  period: string;
  selection_pct: number;
  allocation_pct: number;
  beta_pct: number;
  residual_pct: number;
  total_return_pct: number;
  win_rate: number;
  model_accuracy: number;
}

export const PerformanceApi = {
  getAttribution: (params: PerformanceRequestDTO): Promise<PerformanceResponseDTO> => {
    return ApiClient.fetch<PerformanceResponseDTO>(`/performance/attribution${buildQueryString(params)}`);
  },
  getBrierScores: (): Promise<BrierScoreDTO[]> => {
    return ApiClient.fetch<BrierScoreDTO[]>('/performance/brier-scores');
  },
  getBrinsonAttribution: (): Promise<BrinsonAttributionDTO[]> => {
    return ApiClient.fetch<BrinsonAttributionDTO[]>('/v1/attribution/brinson');
  },
};
