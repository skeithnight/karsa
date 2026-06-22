/**
 * CIO Dashboard Hooks
 * Sprint-16: TanStack Query hooks for dashboard data
 * Phase-5: Consolidated on ApiClient for consistent error handling
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api/client';
import type {
  PortfolioSummaryViewModel,
  RiskTrafficLightViewModel,
  TodayDecisionViewModel,
  StockDecisionViewModel,
  RiskHeatmapViewModel,
  PerformanceAttributionViewModel,
  GovernanceStatusViewModel,
  InvestmentDecisionViewModel,
  ScoreTimeseriesEntryViewModel,
} from '../../features/cio-dashboard/types/viewmodels';
import {
  mapPortfolioSummary,
  mapRiskTrafficLight,
  mapTodayDecision,
  mapStockDecision,
  mapRiskHeatmap,
  mapPerformanceAttribution,
  mapGovernanceStatus,
  mapInvestmentDecision,
  mapScoreTimeseriesEntry,
} from '../../features/cio-dashboard/utils/mappers';

// --- Portfolio Summary ---
export function usePortfolioSummary() {
  return useQuery<PortfolioSummaryViewModel>({
    queryKey: ['cio-dashboard', 'portfolio-summary'],
    queryFn: async () => {
      const data = await ApiClient.fetch<Record<string, unknown>>('/api/portfolio/summary');
      return mapPortfolioSummary(data);
    },
    staleTime: 60_000,
  });
}

// --- Risk Traffic Light ---
export function useRiskTrafficLight() {
  return useQuery<RiskTrafficLightViewModel[]>({
    queryKey: ['cio-dashboard', 'risk-traffic-light'],
    queryFn: async () => {
      const data = await ApiClient.fetch<Record<string, unknown>[]>('/api/risk/traffic-light');
      return Array.isArray(data) ? data.map(mapRiskTrafficLight) : [];
    },
    staleTime: 60_000,
  });
}

// --- Today's Decisions ---
export function useTodayDecisions() {
  return useQuery<TodayDecisionViewModel[]>({
    queryKey: ['cio-dashboard', 'today-decisions'],
    queryFn: async () => {
      const data = await ApiClient.fetch<Record<string, unknown>[]>('/api/decisions/today');
      return Array.isArray(data) ? data.map(mapTodayDecision) : [];
    },
    staleTime: 30_000,
  });
}

// --- Stock Decision ---
export function useStockDecision(ticker: string) {
  return useQuery<StockDecisionViewModel>({
    queryKey: ['cio-dashboard', 'stock-decision', ticker],
    queryFn: async () => {
      const data = await ApiClient.fetch<Record<string, unknown>>(`/api/decisions/${ticker}/latest`);
      return mapStockDecision(data);
    },
    enabled: !!ticker,
    staleTime: 60_000,
  });
}

// --- Risk Heatmap ---
export function useRiskHeatmap() {
  return useQuery<RiskHeatmapViewModel[]>({
    queryKey: ['cio-dashboard', 'risk-heatmap'],
    queryFn: async () => {
      const data = await ApiClient.fetch<Record<string, unknown>[]>('/api/risk/sector-allocation');
      return Array.isArray(data) ? data.map(mapRiskHeatmap) : [];
    },
    staleTime: 60_000,
  });
}

// --- Performance Attribution ---
export function usePerformanceAttribution(period: 'MTD' | 'YTD' = 'YTD') {
  return useQuery<PerformanceAttributionViewModel>({
    queryKey: ['cio-dashboard', 'attribution', period],
    queryFn: async () => {
      const data = await ApiClient.fetch<Record<string, unknown>>(`/api/performance/attribution?period=${period}`);
      return mapPerformanceAttribution(data);
    },
    staleTime: 60_000,
  });
}

// --- Governance Status ---
export function useGovernanceStatus(familyId: string) {
  return useQuery<GovernanceStatusViewModel>({
    queryKey: ['cio-dashboard', 'governance', familyId],
    queryFn: async () => {
      const data = await ApiClient.fetch<Record<string, unknown>>(`/capabilities/${familyId}/governance`);
      return mapGovernanceStatus(data);
    },
    enabled: !!familyId,
    staleTime: 60_000,
  });
}

// --- Investment Decisions ---
export function useInvestmentDecisions(ticker?: string) {
  return useQuery<InvestmentDecisionViewModel[]>({
    queryKey: ['cio-dashboard', 'decisions', ticker],
    queryFn: async () => {
      const path = ticker
        ? `/investments/decisions?ticker=${ticker}`
        : '/investments/decisions';
      const data = await ApiClient.fetch<Record<string, unknown>[]>(path);
      return Array.isArray(data) ? data.map(mapInvestmentDecision) : [];
    },
    staleTime: 30_000,
  });
}

// --- Score Timeseries ---
export function useScoreTimeseries(familyId: string, versionId?: string) {
  return useQuery<ScoreTimeseriesEntryViewModel[]>({
    queryKey: ['cio-dashboard', 'timeseries', familyId, versionId],
    queryFn: async () => {
      const path = versionId
        ? `/capabilities/${familyId}/timeseries?capability_version_id=${versionId}`
        : `/capabilities/${familyId}/timeseries`;
      const data = await ApiClient.fetch<{ entries?: Record<string, unknown>[] }>(path);
      return Array.isArray(data?.entries) ? data.entries.map(mapScoreTimeseriesEntry) : [];
    },
    enabled: !!familyId,
    staleTime: 60_000,
  });
}
