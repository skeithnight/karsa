export interface SectorExposureDTO {
  sector: string;
  allocation_pct: number;
}

export interface PortfolioExposureResponseDTO {
  sectors: SectorExposureDTO[];
}
