/**
 * Dashboard DTO -> ViewModel mappers
 * Sprint-63: Defensive coalescing for all dashboard data
 */

import type {
  PortfolioSummaryDTO,
  RiskMetricDTO,
  EquityCurvePointDTO,
  HoldingDTO,
} from '@/api/endpoints/cio-dashboard';
import type {
  DashboardKpiVM,
  RiskMetricVM,
  EquityPointVM,
  PositionVM,
} from '@/features/dashboard/types/viewmodels';

export function mapDashboardKpis(dto: PortfolioSummaryDTO): DashboardKpiVM {
  return {
    nav: dto.nav ?? 'IDR 0',
    dailyPnl: '—',
    dailyPnlPct: dto.navChangeWtd ?? '0%',
    ytdAlpha: dto.navChangeYtd ?? '0%',
    sharpe: dto.sharpeRatio ?? 0,
    maxDD: dto.maxDrawdownYtd ?? '0%',
    cash: dto.cashPct ?? '0%',
    cashIdle: dto.cashPct ?? '0%',
  };
}

export function mapRiskMetrics(dtos: RiskMetricDTO[]): RiskMetricVM[] {
  return (dtos ?? []).map((dto) => ({
    metric: dto.metric ?? '',
    current: dto.current ?? '',
    limit: dto.limit ?? '',
    utilizationPct: dto.utilizationPct ?? 0,
    status: (dto.status ?? 'GREEN').toLowerCase(),
  }));
}

export function mapEquityCurve(dtos: EquityCurvePointDTO[]): EquityPointVM[] {
  return (dtos ?? []).map((dto) => ({
    timestamp: dto.timestamp ?? '',
    totalEquity: dto.totalEquity ?? 0,
    dailyPnl: dto.dailyPnl ?? 0,
  }));
}

export function mapPositions(dtos: HoldingDTO[]): PositionVM[] {
  return (dtos ?? []).map((dto) => ({
    ticker: dto.ticker ?? '',
    portfolioId: dto.portfolio_id ?? '',
    quantity: dto.quantity ?? 0,
    averageCost: dto.average_cost ?? 0,
    marketValue: dto.market_value ?? 0,
    exposurePct: dto.exposure_pct ?? 0,
    updatedAt: dto.updated_at ?? null,
  }));
}
