/**
 * Positions Hook — Sprint-60
 *
 * Consumes GET /api/cio/positions for the open positions grid.
 * Returns positions with IDX lot sizes and IDR values.
 */
'use client';

import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api/client';

export interface PositionViewModel {
  symbol: string;
  quantityShares: number;
  quantityLots: number;
  avgEntryPrice: number;
  currentPrice: number;
  marketValueIdr: number;
  unrealizedPnlIdr: number;
  unrealizedPnlPct: number;
  sector: string;
}

interface PositionsApiResponse {
  positions: Array<{
    symbol: string;
    quantity_shares: number;
    quantity_lots: number;
    avg_entry_price: number;
    current_price: number;
    market_value_idr: number;
    unrealized_pnl_idr: number;
    unrealized_pnl_pct: number;
    sector: string;
  }>;
  total_market_value_idr: number;
  total_unrealized_pnl_idr: number;
}

function mapPosition(dto: PositionsApiResponse['positions'][0]): PositionViewModel {
  return {
    symbol: dto.symbol,
    quantityShares: dto.quantity_shares,
    quantityLots: dto.quantity_lots,
    avgEntryPrice: dto.avg_entry_price,
    currentPrice: dto.current_price,
    marketValueIdr: dto.market_value_idr,
    unrealizedPnlIdr: dto.unrealized_pnl_idr,
    unrealizedPnlPct: dto.unrealized_pnl_pct,
    sector: dto.sector,
  };
}

export function usePositions() {
  return useQuery<PositionViewModel[]>({
    queryKey: ['cio-dashboard', 'positions'],
    queryFn: async () => {
      const data = await ApiClient.fetch<PositionsApiResponse>('/api/cio/positions');
      return (data.positions ?? []).map(mapPosition);
    },
    staleTime: 5_000,
  });
}
