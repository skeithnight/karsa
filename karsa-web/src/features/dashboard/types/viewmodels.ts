/**
 * Dashboard ViewModel interfaces
 * Sprint-63: CIO Dashboard read models
 */

export interface DashboardKpiVM {
  nav: string;
  dailyPnl: string;
  dailyPnlPct: string;
  ytdAlpha: string;
  sharpe: number;
  maxDD: string;
  cash: string;
  cashIdle: string;
}

export interface RiskMetricVM {
  metric: string;
  current: string;
  limit: string;
  utilizationPct: number;
  status: string;
}

export interface EquityPointVM {
  timestamp: string;
  totalEquity: number;
  dailyPnl: number;
}

export interface PositionVM {
  ticker: string;
  portfolioId: string;
  quantity: number;
  averageCost: number;
  marketValue: number;
  exposurePct: number;
  updatedAt: string | null;
}
