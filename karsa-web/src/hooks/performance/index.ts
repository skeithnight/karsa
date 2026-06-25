import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { PerformanceApi } from "../../api/endpoints/performance";
import {
  mapPerformanceAttribution,
  mapBrinsonAttribution,
  mapCalibration,
  mapPerformanceKpis,
} from "../../features/performance/utils/mappers";
import {
  PerformanceAttributionVM,
  BrinsonAttributionVM,
  CalibrationVM,
  PerformanceKpiVM,
} from "../../features/performance/types/viewmodels";
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

/** Brier score timeseries entry (raw DTO passthrough for calibration charts) */
export interface BrierScoreEntry {
  evaluationSequence: number;
  score: number;
  algorithmVersion: string;
  recordedAt: string;
  capabilityVersionId: string | null;
}

/** Hook to fetch raw Brier score timeseries (used by calibration charts) */
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

/** Hook to fetch Brinson attribution data mapped to BrinsonAttributionVM */
export function useBrinsonAttribution() {
  return useQuery<BrinsonAttributionVM[], ApiError>({
    queryKey: queryKeys.performance.brinsonAttribution(),
    queryFn: async () => {
      const response = await PerformanceApi.getBrinsonAttribution();
      return response.map(mapBrinsonAttribution);
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** Hook to fetch calibration buckets (Brier scores grouped by tier) */
export function useCalibration() {
  return useQuery<CalibrationVM[], ApiError>({
    queryKey: [...queryKeys.performance.brierScores(), "calibration"] as const,
    queryFn: async () => {
      const response = await PerformanceApi.getBrierScores();
      return mapCalibration(response);
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** Hook combining Brinson attribution + Brier scores into unified performance KPIs */
export function usePerformanceKpis() {
  return useQuery<PerformanceKpiVM, ApiError>({
    queryKey: [...queryKeys.performance.brinsonAttribution(), "kpis"] as const,
    queryFn: async () => {
      const [brinson, brier] = await Promise.all([
        PerformanceApi.getBrinsonAttribution(),
        PerformanceApi.getBrierScores(),
      ]);
      return mapPerformanceKpis(brinson, brier);
    },
    staleTime: 5 * 60 * 1000,
  });
}
