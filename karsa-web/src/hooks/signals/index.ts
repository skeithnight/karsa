/**
 * Sprint-63: Signal Hooks
 * Hooks for fetching, approving, and rejecting investment signals.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useListTheses } from '@/hooks/theses';
import { useListMemos } from '@/hooks/memos';
import { InvestmentsApi } from '@/api/endpoints/investments';
import { mapSignals } from '@/features/signals/utils/mappers';
import type { SignalVM } from '@/features/signals/types/viewmodels';

export function useSignals(): { signals: SignalVM[]; isLoading: boolean; error: unknown } {
  const {
    data: thesesData,
    isLoading: isLoadingTheses,
    error: thesesError,
  } = useListTheses({ pagination: { page: 1, size: 100 } });

  const {
    data: memosData,
    isLoading: isLoadingMemos,
    error: memosError,
  } = useListMemos({ pagination: { page: 1, size: 100 } });

  const signals = mapSignals(thesesData?.data, memosData?.data);
  const isLoading = isLoadingTheses || isLoadingMemos;
  const error = thesesError ?? memosError ?? null;

  return { signals, isLoading, error };
}

export function useApproveSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => InvestmentsApi.approveDecision(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['theses'] });
      queryClient.invalidateQueries({ queryKey: ['memos'] });
    },
  });
}

export function useRejectSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => InvestmentsApi.rejectDecision(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['theses'] });
      queryClient.invalidateQueries({ queryKey: ['memos'] });
    },
  });
}
