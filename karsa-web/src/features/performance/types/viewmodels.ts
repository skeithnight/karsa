export interface AttributionVM {
  dateRaw: string;
  dateDisplay: string;
  selectionReturnRaw: number;
  selectionReturnDisplay: string;
  allocationReturnRaw: number;
  allocationReturnDisplay: string;
  betaReturnRaw: number;
  betaReturnDisplay: string;
}

export interface PerformanceAttributionVM {
  data: AttributionVM[];
}

/** Brinson-style attribution row for a single period */
export interface BrinsonAttributionVM {
  period: string;
  periodDisplay: string;
  selectionRaw: number;
  selectionDisplay: string;
  allocationRaw: number;
  allocationDisplay: string;
  betaRaw: number;
  betaDisplay: string;
  residualRaw: number;
  residualDisplay: string;
  totalRaw: number;
  totalDisplay: string;
  winRateRaw: number;
  winRateDisplay: string;
}

/** Calibration tier classification */
export type CalibrationTier = "STRONG" | "MEDIUM" | "WEAK";

/** Calibration bucket grouping Brier scores by tier */
export interface CalibrationVM {
  tier: CalibrationTier;
  tierDisplay: string;
  winPctRaw: number;
  winPctDisplay: string;
  count: number;
  target: number;
}

/** Combined performance KPIs from attribution + calibration */
export interface PerformanceKpiVM {
  ytdReturnRaw: number;
  ytdReturnDisplay: string;
  selectionAlphaRaw: number;
  selectionAlphaDisplay: string;
  allocationAlphaRaw: number;
  allocationAlphaDisplay: string;
  betaDragRaw: number;
  betaDragDisplay: string;
  brierScoreRaw: number;
  brierScoreDisplay: string;
  winRateRaw: number;
  winRateDisplay: string;
}
