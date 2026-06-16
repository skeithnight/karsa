import { PortfolioSummaryResponseDTO } from "../../../types/portfolio/portfolio-summary-response.dto";
import { PortfolioExposureResponseDTO, SectorExposureDTO } from "../../../types/portfolio/portfolio-exposure-response.dto";
import { formatCurrency } from "../../../lib/formatters/currency";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatDate } from "../../../lib/formatters/date";
import { PortfolioSummaryVM, PortfolioExposureVM, SectorExposureVM } from "../types/viewmodels";

export function mapPortfolioSummary(dto: any): PortfolioSummaryVM {
  const aum = dto.net_asset_value || dto.total_aum || 0;
  const pnl = dto.daily_pnl || 0;
  const count = dto.active_theses_count || 0;
  const exposure = dto.net_exposure || 0;
  return {
    totalAumRaw: aum,
    totalAumDisplay: formatCurrency(aum, "USD"),
    dailyPnlRaw: pnl,
    dailyPnlDisplay: formatCurrency(pnl, "USD"),
    activeThesesCount: count,
    netExposureRaw: exposure,
    netExposureDisplay: formatPercentage(exposure, 2),
    lastUpdatedRaw: dto.last_updated || new Date().toISOString(),
    lastUpdatedDisplay: formatDate(dto.last_updated || new Date().toISOString(), "short"),
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
