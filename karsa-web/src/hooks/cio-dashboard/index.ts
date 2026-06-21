/**
 * CIO Dashboard Hooks
 * Sprint-16: TanStack Query hooks for dashboard data
 */

'use client';

import { useQuery } from '@tanstack/react-query';
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

// --- Portfolio Summary ---
async function fetchPortfolioSummary(): Promise<PortfolioSummaryViewModel> {
  const res = await fetch(`${API_BASE}/api/portfolio/summary`);
  if (!res.ok) throw new Error('Failed to fetch portfolio summary');
  return mapPortfolioSummary(await res.json());
}

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ['cio-dashboard', 'portfolio-summary'],
    queryFn: fetchPortfolioSummary,
    staleTime: 60_000,
  });
}

// --- Risk Traffic Light ---
async function fetchRiskTrafficLight(): Promise<RiskTrafficLightViewModel[]> {
  const res = await fetch(`${API_BASE}/api/risk/traffic-light`);
  if (!res.ok) throw new Error('Failed to fetch risk metrics');
  const data = await res.json();
  return Array.isArray(data) ? data.map(mapRiskTrafficLight) : [];
}

export function useRiskTrafficLight() {
  return useQuery({
    queryKey: ['cio-dashboard', 'risk-traffic-light'],
    queryFn: fetchRiskTrafficLight,
    staleTime: 60_000,
  });
}

// --- Today's Decisions ---
async function fetchTodayDecisions(): Promise<TodayDecisionViewModel[]> {
  const res = await fetch(`${API_BASE}/api/decisions/today`);
  if (!res.ok) throw new Error('Failed to fetch decisions');
  const data = await res.json();
  return Array.isArray(data) ? data.map(mapTodayDecision) : [];
}

export function useTodayDecisions() {
  return useQuery({
    queryKey: ['cio-dashboard', 'today-decisions'],
    queryFn: fetchTodayDecisions,
    staleTime: 30_000,
  });
}

// --- Stock Decision ---
async function fetchStockDecision(ticker: string): Promise<StockDecisionViewModel> {
  const res = await fetch(`${API_BASE}/api/decisions/${ticker}/latest`);
  if (!res.ok) throw new Error(`Failed to fetch decision for ${ticker}`);
  return mapStockDecision(await res.json());
}

export function useStockDecision(ticker: string) {
  return useQuery({
    queryKey: ['cio-dashboard', 'stock-decision', ticker],
    queryFn: () => fetchStockDecision(ticker),
    enabled: !!ticker,
    staleTime: 60_000,
  });
}

// --- Risk Heatmap ---
async function fetchRiskHeatmap(): Promise<RiskHeatmapViewModel[]> {
  const res = await fetch(`${API_BASE}/api/risk/sector-allocation`);
  if (!res.ok) throw new Error('Failed to fetch risk heatmap');
  const data = await res.json();
  return Array.isArray(data) ? data.map(mapRiskHeatmap) : [];
}

export function useRiskHeatmap() {
  return useQuery({
    queryKey: ['cio-dashboard', 'risk-heatmap'],
    queryFn: fetchRiskHeatmap,
    staleTime: 60_000,
  });
}

// --- Performance Attribution ---
async function fetchPerformanceAttribution(
  period: 'MTD' | 'YTD' = 'YTD'
): Promise<PerformanceAttributionViewModel> {
  const res = await fetch(`${API_BASE}/api/performance/attribution?period=${period}`);
  if (!res.ok) throw new Error('Failed to fetch attribution');
  return mapPerformanceAttribution(await res.json());
}

export function usePerformanceAttribution(period: 'MTD' | 'YTD' = 'YTD') {
  return useQuery({
    queryKey: ['cio-dashboard', 'attribution', period],
    queryFn: () => fetchPerformanceAttribution(period),
    staleTime: 60_000,
  });
}

// --- Governance Status ---
async function fetchGovernanceStatus(
  familyId: string
): Promise<GovernanceStatusViewModel> {
  const res = await fetch(`${API_BASE}/capabilities/${familyId}/governance`);
  if (!res.ok) throw new Error('Failed to fetch governance status');
  return mapGovernanceStatus(await res.json());
}

export function useGovernanceStatus(familyId: string) {
  return useQuery({
    queryKey: ['cio-dashboard', 'governance', familyId],
    queryFn: () => fetchGovernanceStatus(familyId),
    enabled: !!familyId,
    staleTime: 60_000,
  });
}

// --- Investment Decisions ---
async function fetchInvestmentDecisions(
  ticker?: string
): Promise<InvestmentDecisionViewModel[]> {
  const url = ticker
    ? `${API_BASE}/investments/decisions?ticker=${ticker}`
    : `${API_BASE}/investments/decisions`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch decisions');
  const data = await res.json();
  return Array.isArray(data) ? data.map(mapInvestmentDecision) : [];
}

export function useInvestmentDecisions(ticker?: string) {
  return useQuery({
    queryKey: ['cio-dashboard', 'decisions', ticker],
    queryFn: () => fetchInvestmentDecisions(ticker),
    staleTime: 30_000,
  });
}

// --- Score Timeseries ---
async function fetchScoreTimeseries(
  familyId: string,
  versionId?: string
): Promise<ScoreTimeseriesEntryViewModel[]> {
  const url = versionId
    ? `${API_BASE}/capabilities/${familyId}/timeseries?capability_version_id=${versionId}`
    : `${API_BASE}/capabilities/${familyId}/timeseries`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch timeseries');
  const data = await res.json();
  return Array.isArray(data?.entries) ? data.entries.map(mapScoreTimeseriesEntry) : [];
}

export function useScoreTimeseries(familyId: string, versionId?: string) {
  return useQuery({
    queryKey: ['cio-dashboard', 'timeseries', familyId, versionId],
    queryFn: () => fetchScoreTimeseries(familyId, versionId),
    enabled: !!familyId,
    staleTime: 60_000,
  });
}
