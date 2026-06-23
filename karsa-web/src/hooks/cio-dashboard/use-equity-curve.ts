/**
 * Equity Curve Hook — Sprint-60
 *
 * Consumes GET /api/cio/portfolio/equity-curve for the equity curve chart.
 */
'use client';

import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api/client';

export interface EquityCurvePoint {
  timestamp: string;
  totalEquity: number;
  dailyPnl: number;
}

interface EquityCurveApiResponse {
  timestamp: string;
  total_equity: number;
  daily_pnl: number;
}

function mapPoint(dto: EquityCurveApiResponse): EquityCurvePoint {
  return {
    timestamp: dto.timestamp,
    totalEquity: dto.total_equity,
    dailyPnl: dto.daily_pnl,
  };
}

export function useEquityCurve(timeframe: string = '1D') {
  return useQuery<EquityCurvePoint[]>({
    queryKey: ['cio-dashboard', 'equity-curve', timeframe],
    queryFn: async () => {
      const data = await ApiClient.fetch<EquityCurveApiResponse[]>(
        `/api/cio/portfolio/equity-curve?timeframe=${timeframe}`
      );
      return Array.isArray(data) ? data.map(mapPoint) : [];
    },
    staleTime: 30_000,
  });
}
