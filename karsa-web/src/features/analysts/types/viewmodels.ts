import { StatusBadge } from "../../../lib/formatters/status";

export interface AnalystMetricVM {
  analystId: string;
  role: string;
  trustScoreRaw: number;
  trustScoreDisplay: string;
  winRateRaw: number;
  winRateDisplay: string;
  drawdownRaw: number;
  drawdownDisplay: string;
  performanceStatus: StatusBadge;
}

export interface ListAnalystsVM {
  data: AnalystMetricVM[];
}
