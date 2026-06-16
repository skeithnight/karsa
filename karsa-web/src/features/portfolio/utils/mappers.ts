import { PortfolioSummaryResponseDTO } from "../../../types/portfolio/portfolio-summary-response.dto";
import { PortfolioExposureResponseDTO, SectorExposureDTO } from "../../../types/portfolio/portfolio-exposure-response.dto";
import { formatCurrency } from "../../../lib/formatters/currency";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatDate } from "../../../lib/formatters/date";
import { PortfolioSummaryVM, PortfolioExposureVM, SectorExposureVM } from "../types/viewmodels";

export function mapPortfolioSummary(dto: PortfolioSummaryResponseDTO): PortfolioSummaryVM {
  return {
    totalAumRaw: dto.total_aum,
    totalAumDisplay: formatCurrency(dto.total_aum, "USD"),
    dailyPnlRaw: dto.daily_pnl,
    dailyPnlDisplay: formatCurrency(dto.daily_pnl, "USD"),
    activeThesesCount: dto.active_theses_count,
    netExposureRaw: dto.net_exposure,
    netExposureDisplay: formatPercentage(dto.net_exposure, 2),
    lastUpdatedRaw: dto.last_updated,
    lastUpdatedDisplay: formatDate(dto.last_updated, "short"),
  };
}

export function mapSectorExposure(dto: SectorExposureDTO): SectorExposureVM {
  return {
    sector: dto.sector,
    allocationPctRaw: dto.allocation_pct,
    allocationPctDisplay: formatPercentage(dto.allocation_pct, 2),
  };
}

export function mapPortfolioExposure(dto: PortfolioExposureResponseDTO): PortfolioExposureVM {
  return {
    sectors: (dto.sectors ?? []).map(mapSectorExposure),
  };
}
