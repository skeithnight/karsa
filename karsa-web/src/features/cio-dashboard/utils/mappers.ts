/**
 * CIO Dashboard DTO -> ViewModel Mappers
 * Sprint-16: Defensive coalescing against malformed API responses
 */

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
} from '../types/viewmodels';

/** Safely coalesce null/undefined to fallback */
function coalesce<T>(value: T | null | undefined, fallback: T): T {
  return value ?? fallback;
}

export function mapPortfolioSummary(dto: Record<string, unknown>): PortfolioSummaryViewModel {
  return {
    nav: coalesce(dto.nav as string, 'IDR 0'),
    navChangeWtd: coalesce(dto.navChangeWtd as string, '0%'),
    navChangeYtd: coalesce(dto.navChangeYtd as string, '0%'),
    sharpeRatio: coalesce(dto.sharpeRatio as number, 0),
    maxDrawdownYtd: coalesce(dto.maxDrawdownYtd as string, '0%'),
    activeHoldings: coalesce(dto.activeHoldings as number, 0),
    cashPct: coalesce(dto.cashPct as string, '0%'),
  };
}

export function mapRiskTrafficLight(dto: Record<string, unknown>): RiskTrafficLightViewModel {
  return {
    metric: coalesce(dto.metric as string, ''),
    current: coalesce(dto.current as string, ''),
    limit: coalesce(dto.limit as string, ''),
    utilizationPct: coalesce(dto.utilizationPct as number, 0),
    status: coalesce(dto.status as 'GREEN' | 'AMBER' | 'RED', 'GREEN'),
  };
}

export function mapTodayDecision(dto: Record<string, unknown>): TodayDecisionViewModel {
  return {
    ticker: coalesce(dto.ticker as string, ''),
    action: coalesce(dto.action as 'BUY' | 'HOLD' | 'SELL' | 'ALERT' | 'MONITOR', 'MONITOR'),
    conviction: (dto.conviction as 'STRONG' | 'MEDIUM' | 'WEAK') ?? null,
    targetPrice: (dto.targetPrice as string) ?? null,
    summary: coalesce(dto.summary as string, ''),
    memoId: (dto.memoId as string) ?? null,
  };
}

export function mapStockDecision(dto: Record<string, unknown>): StockDecisionViewModel {
  return {
    ticker: coalesce(dto.ticker as string, ''),
    status: coalesce(dto.status as 'BUY' | 'HOLD' | 'SELL' | 'PASS', 'PASS'),
    currentPrice: coalesce(dto.currentPrice as string, ''),
    entryPrice: (dto.entryPrice as string) ?? null,
    targetPrice: (dto.targetPrice as string) ?? null,
    stopLoss: (dto.stopLoss as string) ?? null,
    positionSizePct: (dto.positionSizePct as string) ?? null,
    convictionLevel: (dto.convictionLevel as 'STRONG' | 'MEDIUM' | 'WEAK') ?? null,
    convictionScore: (dto.convictionScore as number) ?? null,
    analystScores: coalesce(dto.analystScores as Record<string, number>, {}),
    returnSinceEntry: (dto.returnSinceEntry as string) ?? null,
    nextCatalyst: (dto.nextCatalyst as string) ?? null,
    riskFactors: coalesce(dto.riskFactors as string[], []),
  };
}

export function mapRiskHeatmap(dto: Record<string, unknown>): RiskHeatmapViewModel {
  return {
    sector: coalesce(dto.sector as string, ''),
    currentPct: coalesce(dto.currentPct as number, 0),
    limitPct: coalesce(dto.limitPct as number, 0),
    utilizationPct: coalesce(dto.utilizationPct as number, 0),
    status: coalesce(dto.status as 'GREEN' | 'AMBER' | 'RED', 'GREEN'),
  };
}

export function mapPerformanceAttribution(dto: Record<string, unknown>): PerformanceAttributionViewModel {
  return {
    period: coalesce(dto.period as 'MTD' | 'YTD', 'YTD'),
    selectionPct: coalesce(dto.selectionPct as number, 0),
    allocationPct: coalesce(dto.allocationPct as number, 0),
    betaPct: coalesce(dto.betaPct as number, 0),
    residualPct: coalesce(dto.residualPct as number, 0),
    totalReturnPct: coalesce(dto.totalReturnPct as number, 0),
    winRate: coalesce(dto.winRate as number, 0),
    modelAccuracy: coalesce(dto.modelAccuracy as number, 0),
    brierScore: coalesce(dto.brierScore as number, 0),
    calibrationScore: coalesce(dto.calibrationScore as number, 0),
  };
}

export function mapGovernanceStatus(dto: Record<string, unknown>): GovernanceStatusViewModel {
  return {
    status: coalesce(dto.status as 'ACTIVE' | 'SUSPENDED', 'ACTIVE'),
    consecutiveLowScores: coalesce(dto.consecutiveLowScores as number, 0),
    consecutiveHighScores: coalesce(dto.consecutiveHighScores as number, 0),
    suspensionThreshold: coalesce(dto.suspensionThreshold as number, 3),
    unsuspensionThreshold: coalesce(dto.unsuspensionThreshold as number, 2),
  };
}

export function mapInvestmentDecision(dto: Record<string, unknown>): InvestmentDecisionViewModel {
  return {
    decisionId: coalesce(dto.decisionId as string, ''),
    ticker: coalesce(dto.ticker as string, ''),
    decisionDate: coalesce(dto.decisionDate as string, ''),
    state: coalesce(dto.state as string, ''),
    analystCount: coalesce(dto.analystCount as number, 0),
    debateCount: coalesce(dto.debateCount as number, 0),
    hasMemo: coalesce(dto.hasMemo as boolean, false),
    convictionLevel: (dto.convictionLevel as string) ?? null,
    memoDecision: (dto.memoDecision as string) ?? null,
    entryPrice: (dto.entryPrice as string) ?? null,
    exitTarget: (dto.exitTarget as string) ?? null,
  };
}

export function mapScoreTimeseriesEntry(dto: Record<string, unknown>): ScoreTimeseriesEntryViewModel {
  return {
    evaluationSequence: coalesce(dto.evaluationSequence as number, 0),
    score: coalesce(dto.score as number, 0),
    algorithmVersion: coalesce(dto.algorithmVersion as string, ''),
    recordedAt: coalesce(dto.recordedAt as string, ''),
    capabilityVersionId: (dto.capabilityVersionId as string) ?? null,
  };
}
