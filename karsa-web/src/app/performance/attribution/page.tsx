'use client';
import React from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';
import { usePerformanceAttribution } from '../../../hooks/performance';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';

/**
 * Attribution Console
 * Detailed performance attribution breakdown
 */
export default function AttributionPage() {
  const { data, isLoading } = usePerformanceAttribution({
    start_date: '2025-01-01',
    end_date: '2025-12-31',
  });

  return (
    <>
      <PageHeader
        title="Attribution Console"
        description="Performance attribution: selection, allocation, beta, residual"
      />

      {/* Attribution Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 mb-8">
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Selection</div>
          <div className="text-2xl font-mono font-bold">0.00%</div>
          <div className="text-xs text-slate-400">Stock picking</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Allocation</div>
          <div className="text-2xl font-mono font-bold">0.00%</div>
          <div className="text-xs text-slate-400">Position sizing</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Beta</div>
          <div className="text-2xl font-mono font-bold">0.00%</div>
          <div className="text-xs text-slate-400">Market exposure</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Residual</div>
          <div className="text-2xl font-mono font-bold">0.00%</div>
          <div className="text-xs text-slate-400">Fees, friction</div>
        </div>
      </div>

      {/* Attribution Details */}
      <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Attribution History</h3>
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (data?.data?.length ?? 0) > 0 ? (
          <div className="space-y-3">
            {data!.data.map((item, i) => (
              <div key={i} className="flex items-center justify-between border-b pb-2">
                <span className="text-sm font-mono">{item.dateDisplay}</span>
                <div className="flex gap-4">
                  <span className="text-sm">Selection: {item.selectionReturnDisplay}</span>
                  <span className="text-sm">Allocation: {item.allocationReturnDisplay}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No Attribution Data"
            description="Attribution data will appear when positions are tracked."
          />
        )}
      </div>
    </>
  );
}
