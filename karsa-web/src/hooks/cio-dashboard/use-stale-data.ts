/**
 * Stale Data State Hook — Sprint-60
 *
 * Polls /api/cio/stale-data every 5 seconds during market hours.
 * Also receives stale_data_alert via WebSocket (instant).
 */
'use client';

import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api/client';

interface StaleDataState {
  state: 'FRESH' | 'STALE' | 'HALTED';
  last_bar_time: string | null;
}

export function useStaleDataState() {
  return useQuery<StaleDataState>({
    queryKey: ['cio-dashboard', 'stale-data'],
    queryFn: async () => {
      return ApiClient.fetch<StaleDataState>('/api/cio/stale-data');
    },
    staleTime: 5_000,  // 5 seconds — aggressive polling for safety
    refetchInterval: 5_000,  // Auto-refetch every 5s
  });
}
