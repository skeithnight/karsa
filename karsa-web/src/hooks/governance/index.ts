/**
 * Governance Hooks
 * Sprint-63: React Query hooks for CIO Dashboard governance panel
 */

import { useQuery } from '@tanstack/react-query';
import { CioDashboardApi } from '@/api/endpoints/cio-dashboard';
import { GovernanceApi } from '@/api/endpoints/governance';
import { ApiClient } from '@/api/client';
import type { MandateCheckVM, InfrastructureStatusVM } from '@/features/governance/types/viewmodels';
import { mapMandateChecks, mapInfrastructureStatus } from '@/features/governance/utils/mappers';

const STALE_TIME = 60_000;

export function useGovernancePostMortems(params?: { limit?: number }) {
  return useQuery({
    queryKey: ['governance', 'post-mortems', params],
    queryFn: () => GovernanceApi.listPostMortems(params),
    staleTime: STALE_TIME,
  });
}

export function useMandateChecks() {
  return useQuery<MandateCheckVM[]>({
    queryKey: ['governance', 'mandate-checks'],
    queryFn: async () => {
      const metrics = await CioDashboardApi.getRiskTrafficLight();
      return mapMandateChecks(metrics);
    },
    staleTime: STALE_TIME,
  });
}

export function useInfrastructureStatus() {
  return useQuery<InfrastructureStatusVM[]>({
    queryKey: ['governance', 'infrastructure-status'],
    queryFn: async () => {
      const health = await ApiClient.fetch('/health');
      return mapInfrastructureStatus(health as Record<string, unknown>);
    },
    staleTime: STALE_TIME,
  });
}

export interface ConglomerateLimitVM {
  name: string;
  exposurePct: number;
  limitPct: number;
  status: string;
}

export function useConglomerateLimits() {
  return useQuery<ConglomerateLimitVM[]>({
    queryKey: ['governance', 'conglomerate-limits'],
    queryFn: async () => {
      const raw = await CioDashboardApi.getConglomerateExposure();
      if (!Array.isArray(raw)) return [];
      return raw.map((item) => ({
        name: item.group ?? 'Unknown',
        exposurePct: item.exposure_pct ?? 0,
        limitPct: item.limit_pct ?? 0,
        status: item.status ?? 'OK',
      }));
    },
    staleTime: STALE_TIME,
  });
}
