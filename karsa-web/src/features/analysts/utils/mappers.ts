import { AnalystMetricDTO } from "../../../types/analysts/analyst-metric.dto";
import { ListAnalystsResponseDTO } from "../../../types/analysts/list-analysts-response.dto";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatPerformanceState } from "../../../lib/formatters/performance";
import { AnalystMetricVM, ListAnalystsVM } from "../types/viewmodels";

export function mapAnalystMetric(dto: AnalystMetricDTO): AnalystMetricVM {
  // derive performance status
  let state = "NEUTRAL";
  if (dto.win_rate > 0.6) state = "OUTPERFORM";
  else if (dto.win_rate < 0.4) state = "UNDERPERFORM";

  return {
    analystId: dto.analyst_id,
    role: dto.role, // "worker" can be translated to "analyst" inherently via VM naming, but the value can be preserved or mapped
    trustScoreRaw: dto.trust_score,
    trustScoreDisplay: dto.trust_score.toString(),
    winRateRaw: dto.win_rate,
    winRateDisplay: formatPercentage(dto.win_rate, 1),
    drawdownRaw: dto.drawdown,
    drawdownDisplay: formatPercentage(dto.drawdown, 1),
    performanceStatus: formatPerformanceState(state),
  };
}

export function mapListAnalysts(dto: ListAnalystsResponseDTO): ListAnalystsVM {
  return {
    data: (dto.data ?? []).map(mapAnalystMetric),
  };
}
