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

/** Brier score timeseries entry (viewmodel matches DTO for this simple type) */
export interface BrierScoreEntry {
  evaluationSequence: number;
  score: number;
  algorithmVersion: string;
  recordedAt: string;
  capabilityVersionId: string | null;
}

/** Brinson attribution row viewmodel */
export interface BrinsonAttributionEntry {
  period: string;
  selectionPct: number;
  allocationPct: number;
  betaPct: number;
  residualPct: number;
  totalReturnPct: number;
  winRate: number;
  modelAccuracy: number;
}

/** Hook to fetch Brier score timeseries */
export function useBrierScores() {
  return useQuery<BrierScoreEntry[], ApiError>({
    queryKey: queryKeys.performance.brierScores(),
    queryFn: async () => {
      const response = await PerformanceApi.getBrierScores();
      return response.map((dto) => ({
        evaluationSequence: dto.evaluation_sequence,
        score: dto.score,
        algorithmVersion: dto.algorithm_version,
        recordedAt: dto.recorded_at,
        capabilityVersionId: dto.capability_version_id,
      }));
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** Hook to fetch Brinson attribution data */
export function useBrinsonAttribution() {
  return useQuery<BrinsonAttributionEntry[], ApiError>({
    queryKey: queryKeys.performance.brinsonAttribution(),
    queryFn: async () => {
      const response = await PerformanceApi.getBrinsonAttribution();
      return response.map((dto) => ({
        period: dto.period,
        selectionPct: dto.selection_pct,
        allocationPct: dto.allocation_pct,
        betaPct: dto.beta_pct,
        residualPct: dto.residual_pct,
        totalReturnPct: dto.total_return_pct,
        winRate: dto.win_rate,
        modelAccuracy: dto.model_accuracy,
      }));
    },
    staleTime: 5 * 60 * 1000,
  });
}
