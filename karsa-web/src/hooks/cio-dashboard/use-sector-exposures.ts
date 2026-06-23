/**
 * Sector Exposures Hook — Sprint-60
 *
 * Consumes GET /api/cio/exposures/sectors for the sector exposure grid.
 */
'use client';

import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api/client';

export interface SectorExposureViewModel {
  sectorName: string;
  grossExposureIdr: number;
  netExposureIdr: number;
}

interface SectorExposureApiResponse {
  sector_name: string;
  gross_exposure: number;
  net_exposure: number;
}

function mapSector(dto: SectorExposureApiResponse): SectorExposureViewModel {
  return {
    sectorName: dto.sector_name,
    grossExposureIdr: dto.gross_exposure,
    netExposureIdr: dto.net_exposure,
  };
}

export function useSectorExposures() {
  return useQuery<SectorExposureViewModel[]>({
    queryKey: ['cio-dashboard', 'sector-exposures'],
    queryFn: async () => {
      const data = await ApiClient.fetch<SectorExposureApiResponse[]>(
        '/api/cio/exposures/sectors'
      );
      return Array.isArray(data) ? data.map(mapSector) : [];
    },
    staleTime: 30_000,
  });
}
