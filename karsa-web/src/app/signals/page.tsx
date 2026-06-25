'use client';
import React, { useState } from 'react';
import { PageHeader } from '@/components/shared/PageHeader';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { ApiClient } from '@/api/client';
import { useQuery } from '@tanstack/react-query';

interface SignalResult {
  type: string;
  id: string;
  label: string;
  ticker: string;
  action: string;
  conviction: string;
  rationale: string;
  entry_price: string | null;
  exit_target: string | null;
  stop_loss: string | null;
  position_size_pct: string | null;
}

function useSignals(search: string) {
  return useQuery<{ results: SignalResult[] }>({
    queryKey: ['signals', search],
    queryFn: () => ApiClient.fetch(`/search?q=${encodeURIComponent(search || 'BUY')}`),
    staleTime: 30_000,
  });
}

function useApproveSignal() {
  return { mutate: (id: string) => console.log('Approve:', id), isPending: false };
}
function useRejectSignal() {
  return { mutate: (id: string) => console.log('Reject:', id), isPending: false };
}

type FilterTab = 'All' | 'Pending' | 'Approved' | 'Rejected';
type SortBy = 'conviction' | 'action' | 'ticker' | 'risk-reward';
const FILTER_TABS: FilterTab[] = ['All', 'Pending', 'Approved', 'Rejected'];
const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: 'conviction', label: 'Conviction' },
  { value: 'risk-reward', label: 'Risk/Reward' },
  { value: 'action', label: 'Action' },
  { value: 'ticker', label: 'Ticker' },
];

const ACTION_STYLES: Record<string, string> = {
  BUY: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  SELL: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  HOLD: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
};

const CONVICTION_COLORS: Record<string, string> = {
  STRONG: 'text-emerald-400',
  MEDIUM: 'text-amber-400',
  WEAK: 'text-red-400',
};

function ConvictionPips({ level }: { level: number }) {
  return (
    <div className="flex gap-1">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className={`w-2 h-2 rounded-full ${i < level ? 'bg-indigo-500' : 'bg-gray-700'}`} />
      ))}
    </div>
  );
}

export default function SignalsPage() {
  const [activeTab, setActiveTab] = useState<FilterTab>('All');
  const [sortBy, setSortBy] = useState<SortBy>('conviction');
  const [searchQuery, setSearchQuery] = useState('BUY');
  const { data, isLoading } = useSignals(searchQuery);
  const approveMutation = useApproveSignal();
  const rejectMutation = useRejectSignal();

  const signals = (data?.results ?? []).filter((r) => r.type === 'DECISION');
  const filteredSignals = (activeTab === 'All' ? signals : signals.filter((s) => {
    if (activeTab === 'Pending') return true;
    if (activeTab === 'Approved') return true;
    return true;
  })).sort((a, b) => {
    if (sortBy === 'conviction') {
      const order = { STRONG: 0, MEDIUM: 1, WEAK: 2 };
      return (order[a.conviction as keyof typeof order] ?? 3) - (order[b.conviction as keyof typeof order] ?? 3);
    }
    if (sortBy === 'action') return a.action.localeCompare(b.action);
    if (sortBy === 'ticker') return a.ticker.localeCompare(b.ticker);
    if (sortBy === 'risk-reward') {
      const rrA = a.entry_price && a.exit_target && a.stop_loss ? (parseFloat(a.exit_target) - parseFloat(a.entry_price)) / (parseFloat(a.entry_price) - parseFloat(a.stop_loss)) : 0;
      const rrB = b.entry_price && b.exit_target && b.stop_loss ? (parseFloat(b.exit_target) - parseFloat(b.entry_price)) / (parseFloat(b.entry_price) - parseFloat(b.stop_loss)) : 0;
      return rrB - rrA;
    }
    return 0;
  });

  return (
    <>
      <PageHeader title="Signal Hub" description="Review and act on investment signals" />

      <div className="mt-4 flex gap-3">
        <input
          type="text"
          placeholder="Search tickers (BBCA, TLKM...) or actions (BUY, SELL)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-indigo-500"
        />
      </div>

      <div className="mt-4 flex items-center gap-2">
        {FILTER_TABS.map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700'
            }`}>
            {tab}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-slate-500">Sort:</span>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="px-3 py-1.5 text-xs rounded-lg bg-gray-800 border border-gray-700 text-gray-300 focus:outline-none focus:border-indigo-500">
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {isLoading ? (
          <LoadingSkeleton variant="card" />
        ) : filteredSignals.length === 0 ? (
          <EmptyState title="No Signals" description="No signals found. Try searching for a ticker or action." />
        ) : (
          filteredSignals.map((signal) => {
            const entry = signal.entry_price ? parseFloat(signal.entry_price) : 0;
            const target = signal.exit_target ? parseFloat(signal.exit_target) : 0;
            const stop = signal.stop_loss ? parseFloat(signal.stop_loss) : 0;
            const riskReward = entry && stop ? ((target - entry) / (entry - stop)).toFixed(1) : '—';
            const upside = entry && target ? (((target - entry) / entry) * 100).toFixed(1) : '—';
            const convLevel = signal.conviction === 'STRONG' ? 4 : signal.conviction === 'MEDIUM' ? 3 : 2;

            return (
              <Card key={signal.id} className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${ACTION_STYLES[signal.action] ?? ACTION_STYLES.HOLD}`}>
                      {signal.action}
                    </span>
                    <span className="text-lg font-semibold">{signal.ticker}</span>
                    <span className={`text-xs font-medium ${CONVICTION_COLORS[signal.conviction] ?? 'text-gray-400'}`}>
                      {signal.conviction} {signal.conviction && `${convLevel}/5`}
                    </span>
                    <ConvictionPips level={convLevel} />
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="default" onClick={() => approveMutation.mutate(signal.id)} disabled={approveMutation.isPending}>Approve</Button>
                    <Button size="sm" variant="destructive" onClick={() => rejectMutation.mutate(signal.id)} disabled={rejectMutation.isPending}>Reject</Button>
                  </div>
                </div>

                <p className="mt-3 text-sm text-slate-400 line-clamp-2">{signal.rationale}</p>

                {entry > 0 && (
                  <div className="mt-3 flex flex-wrap items-center gap-4 text-xs font-mono">
                    <span className="text-slate-500">Entry: <span className="text-slate-300">{entry.toLocaleString()}</span></span>
                    <span className="text-slate-500">Target: <span className="text-emerald-400">{target.toLocaleString()} (+{upside}%)</span></span>
                    <span className="text-slate-500">Stop: <span className="text-red-400">{stop.toLocaleString()}</span></span>
                    {signal.position_size_pct && <span className="text-slate-500">Size: <span className="text-slate-300">{signal.position_size_pct}% NAV</span></span>}
                    <span className="text-slate-500">R:R: <span className="text-indigo-400">1:{riskReward}</span></span>
                  </div>
                )}
              </Card>
            );
          })
        )}
      </div>
    </>
  );
}
