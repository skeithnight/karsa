import { AttributionDTO } from "../../../types/performance/attribution.dto";
import { PerformanceResponseDTO } from "../../../types/performance/performance-response.dto";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatDate } from "../../../lib/formatters/date";
import { AttributionVM, PerformanceAttributionVM } from "../types/viewmodels";

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
