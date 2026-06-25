import { ApiClient } from "../client";

/** Portfolio summary from CIO Dashboard */
export interface PortfolioSummaryDTO {
  nav: string;
  navChangeWtd: string;
  navChangeYtd: string;
  sharpeRatio: number;
  maxDrawdownYtd: string;
  activeHoldings: number;
  cashPct: string;
  last_updated: string;
}

/** Portfolio holding from CIO Dashboard */
export interface HoldingDTO {
  ticker: string;
  portfolio_id: string;
  quantity: number;
  average_cost: number;
  market_value: number;
  exposure_pct: number;
  updated_at: string | null;
}

/** Risk traffic light metric */
export interface RiskMetricDTO {
  metric: string;
  current: string;
  limit: string;
  utilizationPct: number;
  status: "GREEN" | "AMBER" | "RED";
}

/** Today's decision */
export interface DecisionTodayDTO {
  ticker: string;
  action: string;
  conviction: string | null;
  targetPrice: string | null;
  summary: string;
  memoId: string | null;
  source: string;
}

/** Latest stock decision */
export interface StockDecisionDTO {
  ticker: string;
  status: string;
  currentPrice: string;
  entryPrice: string | null;
  targetPrice: string | null;
  stopLoss: string | null;
  positionSizePct: string | null;
  convictionLevel: string | null;
  convictionScore: number | null;
  analystScores: Record<string, number>;
  returnSinceEntry: number | null;
  nextCatalyst: string | null;
  riskFactors: string[];
}

/** Sector allocation for risk heatmap */
export interface SectorAllocationDTO {
  sector: string;
  currentPct: number;
  limitPct: number;
  utilizationPct: number;
  status: string;
}

/** Performance attribution breakdown */
export interface PerformanceAttributionDTO {
  period: string;
  selectionPct: number;
  allocationPct: number;
  betaPct: number;
  residualPct: number;
  totalReturnPct: number;
  winRate: number;
  modelAccuracy: number;
}

/** Conglomerate exposure */
export interface ConglomerateExposureDTO {
  group: string;
  tickers: string[];
  total_exposure_idr: number;
  exposure_pct: number;
  limit_pct: number;
  status: "OK" | "WARNING" | "BREACH";
}

/** Equity curve data point */
export interface EquityCurvePointDTO {
  timestamp: string;
  totalEquity: number;
  dailyPnl: number;
}

/** Sector exposure */
export interface SectorExposureDTO {
  sectorName: string;
  grossExposureIdr: number;
  netExposureIdr: number;
}

export const CioDashboardApi = {
  getPortfolioSummary: (): Promise<PortfolioSummaryDTO> => {
    return ApiClient.fetch<PortfolioSummaryDTO>("/portfolio/summary");
  },

  getHoldings: (): Promise<HoldingDTO[]> => {
    return ApiClient.fetch<HoldingDTO[]>("/portfolio/holdings");
  },

  getRiskTrafficLight: (): Promise<RiskMetricDTO[]> => {
    return ApiClient.fetch<RiskMetricDTO[]>("/risk/traffic-light");
  },

  getDecisionsToday: (): Promise<DecisionTodayDTO[]> => {
    return ApiClient.fetch<DecisionTodayDTO[]>("/decisions/today");
  },

  getLatestDecision: (ticker: string): Promise<StockDecisionDTO> => {
    return ApiClient.fetch<StockDecisionDTO>(`/decisions/${ticker}/latest`);
  },

  getSectorAllocation: (): Promise<SectorAllocationDTO[]> => {
    return ApiClient.fetch<SectorAllocationDTO[]>("/risk/sector-allocation");
  },

  getPerformanceAttribution: (period: string = "YTD"): Promise<PerformanceAttributionDTO> => {
    return ApiClient.fetch<PerformanceAttributionDTO>(`/performance/attribution?period=${period}`);
  },

  getConglomerateExposure: (): Promise<ConglomerateExposureDTO[]> => {
    return ApiClient.fetch<ConglomerateExposureDTO[]>("/exposures/conglomerates");
  },

  getEquityCurve: (timeframe: string = "1M"): Promise<EquityCurvePointDTO[]> => {
    return ApiClient.fetch<EquityCurvePointDTO[]>(`/cio/portfolio/equity-curve?timeframe=${timeframe}`);
  },

  getSectorExposure: (): Promise<SectorExposureDTO[]> => {
    return ApiClient.fetch<SectorExposureDTO[]>("/cio/exposures/sectors");
  },
};
