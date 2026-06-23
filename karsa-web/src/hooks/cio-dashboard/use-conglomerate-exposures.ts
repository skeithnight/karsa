/**
 * Conglomerate Exposures Hook -- Sprint-59
 *
 * Consumes GET /api/cio/exposures/conglomerates for the conglomerate
 * heatmap visualization on the CIO Dashboard.
 */
'use client';

import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api/client';

export interface ConglomerateExposureViewModel {
  group: string;
  tickers: string[];
  totalExposureIdr: number;
  exposurePct: number;
  limitPct: number;
  status: 'OK' | 'WARNING' | 'BREACH';
}

interface ConglomerateExposureApiResponse {
  group: string;
  tickers: string[];
  total_exposure_idr: number;
  exposure_pct: number;
  limit_pct: number;
  status: 'OK' | 'WARNING' | 'BREACH';
}

function mapConglomerate(dto: ConglomerateExposureApiResponse): ConglomerateExposureViewModel {
  return {
    group: dto.group,
    tickers: Array.isArray(dto.tickers) ? dto.tickers : [],
    totalExposureIdr: dto.total_exposure_idr ?? 0,
    exposurePct: dto.exposure_pct ?? 0,
    limitPct: dto.limit_pct ?? 0,
    status: dto.status ?? 'OK',
  };
}

export function useConglomerateExposures() {
  return useQuery<ConglomerateExposureViewModel[]>({
    queryKey: ['cio-dashboard', 'conglomerate-exposures'],
    queryFn: async () => {
      const data = await ApiClient.fetch<ConglomerateExposureApiResponse[]>(
        '/api/cio/exposures/conglomerates'
      );
      return Array.isArray(data) ? data.map(mapConglomerate) : [];
    },
    staleTime: 30_000,
  });
}
