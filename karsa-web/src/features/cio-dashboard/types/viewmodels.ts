/**
 * CIO Dashboard ViewModels
 * Sprint-16: DTO -> ViewModel mapping types
 */

/** Portfolio summary for Tier 1 executive view */
export interface PortfolioSummaryViewModel {
  nav: string; // "IDR 10.2B"
  navChangeWtd: string; // "+2.1%"
  navChangeYtd: string; // "+15.3%"
  sharpeRatio: number;
  maxDrawdownYtd: string; // "8.2%"
  activeHoldings: number;
  cashPct: string; // "5%"
  last_updated?: string | null; // ISO 8601 timestamp
}

/** Risk traffic light for Tier 1 */
export interface RiskTrafficLightViewModel {
  metric: string;
  current: string;
  limit: string;
  utilizationPct: number; // 0-100
  status: 'GREEN' | 'AMBER' | 'RED';
}

/** Today's decision card for Tier 1 */
export interface TodayDecisionViewModel {
  ticker: string;
  action: 'BUY' | 'HOLD' | 'SELL' | 'ALERT' | 'MONITOR';
  conviction: 'STRONG' | 'MEDIUM' | 'WEAK' | null;
  targetPrice: string | null;
  summary: string;
  memoId: string | null;
}

/** Stock decision card for Tier 2 */
export interface StockDecisionViewModel {
  ticker: string;
  status: 'BUY' | 'HOLD' | 'SELL' | 'PASS';
  currentPrice: string;
  entryPrice: string | null;
  targetPrice: string | null;
  stopLoss: string | null;
  positionSizePct: string | null;
  convictionLevel: 'STRONG' | 'MEDIUM' | 'WEAK' | null;
  convictionScore: number | null;
  analystScores: Record<string, number>;
  returnSinceEntry: string | null;
  nextCatalyst: string | null;
  riskFactors: string[];
}

/** Risk heatmap data */
export interface RiskHeatmapViewModel {
  sector: string;
  currentPct: number;
  limitPct: number;
  utilizationPct: number;
  status: 'GREEN' | 'AMBER' | 'RED';
}

/** Performance attribution */
export interface PerformanceAttributionViewModel {
  period: 'MTD' | 'YTD';
  selectionPct: number;
  allocationPct: number;
  betaPct: number;
  residualPct: number;
  totalReturnPct: number;
  winRate: number;
  modelAccuracy: number;
  brierScore: number;
  calibrationScore: number;
}

/** Governance status */
export interface GovernanceStatusViewModel {
  status: 'ACTIVE' | 'SUSPENDED';
  consecutiveLowScores: number;
  consecutiveHighScores: number;
  suspensionThreshold: number;
  unsuspensionThreshold: number;
}

/** Investment decision for query */
export interface InvestmentDecisionViewModel {
  decisionId: string;
  ticker: string;
  decisionDate: string;
  state: string;
  analystCount: number;
  debateCount: number;
  hasMemo: boolean;
  convictionLevel: string | null;
  memoDecision: string | null;
  entryPrice: string | null;
  exitTarget: string | null;
}

/** Score timeseries entry */
export interface ScoreTimeseriesEntryViewModel {
  evaluationSequence: number;
  score: number;
  algorithmVersion: string;
  recordedAt: string;
  capabilityVersionId: string | null;
}
