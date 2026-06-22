'use client';
import React from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';
import { useInvestmentDecisions } from '../../../hooks/cio-dashboard';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';

/**
 * Forecast Quality Console
 * Tracks forecast accuracy and calibration
 */
export default function ForecastsPage() {
  const { data: decisions, isLoading } = useInvestmentDecisions();

  // Compute forecast metrics from decisions
  const totalDecisions = decisions?.length ?? 0;
  const approvedDecisions = decisions?.filter(d => d.state === 'APPROVED') ?? [];
  const withTargets = approvedDecisions.filter(d => d.exitTarget);

  return (
    <>
      <PageHeader
        title="Forecast Quality"
        description="Track forecast accuracy and calibration over time"
      />

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 mb-8">
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Total Forecasts</div>
          <div className="text-2xl font-mono font-bold">{isLoading ? '...' : totalDecisions}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Approved</div>
          <div className="text-2xl font-mono font-bold text-emerald-600">{isLoading ? '...' : approvedDecisions.length}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">With Targets</div>
          <div className="text-2xl font-mono font-bold">{isLoading ? '...' : withTargets.length}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Calibration Score</div>
          <div className="text-2xl font-mono font-bold text-slate-400">N/A</div>
        </div>
      </div>

      {/* Forecast Table */}
      <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Forecast History</h3>
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : approvedDecisions.length > 0 ? (
          <div className="space-y-3">
            {approvedDecisions.map((d, i) => (
              <div key={i} className="flex items-center justify-between border-b pb-2">
                <div>
                  <span className="font-semibold">{d.ticker}</span>
                  <span className="text-sm text-slate-500 ml-2">{d.state}</span>
                </div>
                <div className="flex items-center gap-4">
                  {d.entryPrice && (
                    <span className="text-sm font-mono">Entry: {d.entryPrice}</span>
                  )}
                  {d.exitTarget && (
                    <span className="text-sm font-mono">Target: {d.exitTarget}</span>
                  )}
                  {d.convictionLevel && (
                    <span className={`text-xs px-2 py-1 rounded ${
                      d.convictionLevel === 'STRONG' ? 'bg-emerald-100 text-emerald-800' :
                      d.convictionLevel === 'MEDIUM' ? 'bg-amber-100 text-amber-800' :
                      'bg-slate-100 text-slate-800'
                    }`}>
                      {d.convictionLevel}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No Forecasts"
            description="Forecast data will appear when investment decisions are tracked."
          />
        )}
      </div>
    </>
  );
}
