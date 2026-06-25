/**
 * Dashboard React Query hooks
 * Sprint-63: CIO Dashboard data fetching
 */

import { useQuery } from '@tanstack/react-query';
import { CioDashboardApi } from '@/api/endpoints/cio-dashboard';
import type { DashboardKpiVM } from '@/features/dashboard/types/viewmodels';
import { mapDashboardKpis } from '@/features/dashboard/utils/mappers';

const STALE_TIME = 60_000;

export function useRiskTrafficLight() {
  return useQuery({
    queryKey: ['dashboard', 'risk-traffic-light'] as const,
    queryFn: () => CioDashboardApi.getRiskTrafficLight(),
    staleTime: STALE_TIME,
  });
}

export function useEquityCurve(timeframe?: string) {
  return useQuery({
    queryKey: ['dashboard', 'equity-curve', timeframe ?? '1M'] as const,
    queryFn: () => CioDashboardApi.getEquityCurve(timeframe),
    staleTime: STALE_TIME,
  });
}

export function useHoldings() {
  return useQuery({
    queryKey: ['dashboard', 'holdings'] as const,
    queryFn: () => CioDashboardApi.getHoldings(),
    staleTime: STALE_TIME,
  });
}

export function useSectorExposure() {
  return useQuery({
    queryKey: ['dashboard', 'sector-exposure'] as const,
    queryFn: () => CioDashboardApi.getSectorExposure(),
    staleTime: STALE_TIME,
  });
}

export function useConglomerateExposure() {
  return useQuery({
    queryKey: ['dashboard', 'conglomerate-exposure'] as const,
    queryFn: () => CioDashboardApi.getConglomerateExposure(),
    staleTime: STALE_TIME,
  });
}

export function useDashboardKpis() {
  return useQuery<DashboardKpiVM>({
    queryKey: ['dashboard', 'kpis'] as const,
    queryFn: async () => {
      const dto = await CioDashboardApi.getPortfolioSummary();
      return mapDashboardKpis(dto);
    },
    staleTime: STALE_TIME,
  });
}
