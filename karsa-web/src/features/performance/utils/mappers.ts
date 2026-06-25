import { AttributionDTO } from "../../../types/performance/attribution.dto";
import { PerformanceResponseDTO } from "../../../types/performance/performance-response.dto";
import { BrinsonAttributionDTO } from "../../../api/endpoints/performance";
import { BrierScoreDTO } from "../../../api/endpoints/performance";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatDate } from "../../../lib/formatters/date";
import {
  AttributionVM,
  PerformanceAttributionVM,
  BrinsonAttributionVM,
  CalibrationVM,
  CalibrationTier,
  PerformanceKpiVM,
} from "../types/viewmodels";

export function mapAttribution(dto: AttributionDTO): AttributionVM {
  return {
    dateRaw: dto.date,
    dateDisplay: formatDate(dto.date, "short"),
    selectionReturnRaw: dto.selection_return,
    selectionReturnDisplay: formatPercentage(dto.selection_return, 2),
    allocationReturnRaw: dto.allocation_return,
    allocationReturnDisplay: formatPercentage(dto.allocation_return, 2),
    betaReturnRaw: dto.beta_return,
    betaReturnDisplay: formatPercentage(dto.beta_return, 2),
  };
}

export function mapPerformanceAttribution(dto: PerformanceResponseDTO): PerformanceAttributionVM {
  return {
    data: (dto.data ?? []).map(mapAttribution),
  };
}

/** Map a single BrinsonAttributionDTO row to BrinsonAttributionVM */
export function mapBrinsonAttribution(dto: BrinsonAttributionDTO): BrinsonAttributionVM {
  return {
    period: dto.period,
    periodDisplay: dto.period,
    selectionRaw: dto.selection_pct,
    selectionDisplay: formatPercentage(dto.selection_pct, 2),
    allocationRaw: dto.allocation_pct,
    allocationDisplay: formatPercentage(dto.allocation_pct, 2),
    betaRaw: dto.beta_pct,
    betaDisplay: formatPercentage(dto.beta_pct, 2),
    residualRaw: dto.residual_pct,
    residualDisplay: formatPercentage(dto.residual_pct, 2),
    totalRaw: dto.total_return_pct,
    totalDisplay: formatPercentage(dto.total_return_pct, 2),
    winRateRaw: dto.win_rate,
    winRateDisplay: formatPercentage(dto.win_rate, 1),
  };
}

/** Classify a Brier score into a calibration tier */
export function classifyBrierTier(score: number): CalibrationTier {
  if (score >= 4) return "STRONG";
  if (score === 3) return "MEDIUM";
  return "WEAK";
}

const TIER_TARGETS: Record<CalibrationTier, number> = {
  STRONG: 4,
  MEDIUM: 3,
  WEAK: 2,
};

const TIER_DISPLAY: Record<CalibrationTier, string> = {
  STRONG: "Strong (>=4)",
  MEDIUM: "Medium (=3)",
  WEAK: "Weak (<=2)",
};

/** Map Brier score timeseries into calibration buckets grouped by tier */
export function mapCalibration(dtos: BrierScoreDTO[]): CalibrationVM[] {
  const buckets: Record<CalibrationTier, { winSum: number; count: number }> = {
    STRONG: { winSum: 0, count: 0 },
    MEDIUM: { winSum: 0, count: 0 },
    WEAK: { winSum: 0, count: 0 },
  };

  for (const dto of dtos) {
    const tier = classifyBrierTier(dto.score);
    buckets[tier].winSum += dto.score;
    buckets[tier].count += 1;
  }

  const tiers: CalibrationTier[] = ["STRONG", "MEDIUM", "WEAK"];
  return tiers.map((tier) => {
    const { winSum, count } = buckets[tier];
    const winPct = count > 0 ? winSum / count : 0;
    return {
      tier,
      tierDisplay: TIER_DISPLAY[tier],
      winPctRaw: winPct,
      winPctDisplay: formatPercentage(winPct, 1),
      count,
      target: TIER_TARGETS[tier],
    };
  });
}

/** Derive combined performance KPIs from Brinson attribution rows and Brier scores */
export function mapPerformanceKpis(
  brinson: BrinsonAttributionDTO[],
  brier: BrierScoreDTO[],
): PerformanceKpiVM {
  // Aggregate latest-period Brinson data for KPI display
  const latest = brinson.length > 0 ? brinson[brinson.length - 1] : null;

  const ytdReturn = latest?.total_return_pct ?? 0;
  const selectionAlpha = latest?.selection_pct ?? 0;
  const allocationAlpha = latest?.allocation_pct ?? 0;
  const betaDrag = latest?.beta_pct ?? 0;
  const winRate = latest?.win_rate ?? 0;

  // Average Brier score across all evaluations
  const avgBrier =
    brier.length > 0
      ? brier.reduce((sum, b) => sum + b.score, 0) / brier.length
      : 0;

  return {
    ytdReturnRaw: ytdReturn,
    ytdReturnDisplay: formatPercentage(ytdReturn, 2),
    selectionAlphaRaw: selectionAlpha,
    selectionAlphaDisplay: formatPercentage(selectionAlpha, 2),
    allocationAlphaRaw: allocationAlpha,
    allocationAlphaDisplay: formatPercentage(allocationAlpha, 2),
    betaDragRaw: betaDrag,
    betaDragDisplay: formatPercentage(betaDrag, 2),
    brierScoreRaw: avgBrier,
    brierScoreDisplay: avgBrier.toFixed(2),
    winRateRaw: winRate,
    winRateDisplay: formatPercentage(winRate, 1),
  };
}
