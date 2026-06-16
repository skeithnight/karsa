import { StatusBadge } from "../../../lib/formatters/status";

export interface PortfolioSummaryVM {
  totalAumRaw: number;
  totalAumDisplay: string;
  dailyPnlRaw: number;
  dailyPnlDisplay: string;
  activeThesesCount: number;
  netExposureRaw: number;
  netExposureDisplay: string;
  lastUpdatedRaw: string;
  lastUpdatedDisplay: string;
}

export interface SectorExposureVM {
  sector: string;
  allocationPctRaw: number;
  allocationPctDisplay: string;
}

export interface PortfolioExposureVM {
  sectors: SectorExposureVM[];
}
