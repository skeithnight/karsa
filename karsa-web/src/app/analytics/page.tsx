'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { EmptyState } from '../../components/shared/EmptyState';
import { usePerformanceAttribution } from '../../hooks/performance';
import { useInvestmentDecisions } from '../../hooks/cio-dashboard';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';

/**
 * Analytics Dashboard
 * Phase-4/5: Win rates, calibration, research quality, forecast quality
 */
export default function AnalyticsPage() {
  const { data: attribution, isLoading: loadingAttribution } = usePerformanceAttribution({
    start_date: '2025-01-01',
    end_date: '2025-12-31',
  });
  const { data: decisions, isLoading: loadingDecisions } = useInvestmentDecisions();

  const decisionCount = decisions?.length ?? 0;
  const approvedCount = decisions?.filter(d => d.state === 'APPROVED').length ?? 0;
  const rejectedCount = decisions?.filter(d => d.state === 'REJECTED').length ?? 0;
  const pendingCount = decisions?.filter(d => d.state === 'PENDING' || d.state === 'PROPOSED').length ?? 0;
  const memoCount = decisions?.filter(d => d.hasMemo).length ?? 0;

  // Decision state breakdown
  const stateBreakdown = [
    { label: 'Approved', count: approvedCount, color: 'bg-emerald-500' },
    { label: 'Rejected', count: rejectedCount, color: 'bg-red-500' },
    { label: 'Pending', count: pendingCount, color: 'bg-amber-500' },
    { label: 'Other', count: Math.max(0, decisionCount - approvedCount - rejectedCount - pendingCount), color: 'bg-slate-400' },
  ];

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Win rates, calibration, research quality, and forecast accuracy"
      />

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 mb-8">
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Total Decisions</div>
          <div className="text-2xl font-mono font-bold">{loadingDecisions ? '...' : decisionCount}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Approved</div>
          <div className="text-2xl font-mono font-bold text-emerald-600">{loadingDecisions ? '...' : approvedCount}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">With Memos</div>
          <div className="text-2xl font-mono font-bold">{loadingDecisions ? '...' : memoCount}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Attribution Periods</div>
          <div className="text-2xl font-mono font-bold">{loadingAttribution ? '...' : (attribution?.data?.length ?? 0)}</div>
        </div>
      </div>

      {/* Decision State Breakdown */}
      <div className="border rounded-xl p-6 bg-white dark:bg-slate-900 mb-6">
        <h3 className="text-lg font-semibold mb-4">Decision State Breakdown</h3>
        {loadingDecisions ? (
          <LoadingSkeleton variant="card" />
        ) : decisionCount > 0 ? (
          <div className="space-y-3">
            {stateBreakdown.map(item => (
              <div key={item.label} className="flex items-center justify-between">
                <span className="text-sm font-medium">{item.label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono">{item.count}</span>
                  <div className="w-32 h-3 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item.color} rounded-full`}
                      style={{ width: `${(item.count / decisionCount) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-mono w-12 text-right">
                    {((item.count / decisionCount) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No Decisions" description="No decisions to analyze." />
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Win Rates */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Win Rates by Category</h3>
          {loadingDecisions ? (
            <LoadingSkeleton variant="card" />
          ) : decisionCount > 0 ? (
            <div className="space-y-3">
              <WinRateRow label="Overall" total={decisionCount} won={approvedCount} />
              <WinRateRow label="With Memos" total={decisionCount} won={memoCount} />
            </div>
          ) : (
            <EmptyState
              title="No Win Rate Data"
              description="Win rates will appear when decisions are tracked."
            />
          )}
        </div>

        {/* Conviction Calibration */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Conviction Calibration</h3>
          {loadingDecisions ? (
            <LoadingSkeleton variant="card" />
          ) : decisionCount > 0 ? (
            <div className="space-y-3">
              {['STRONG', 'MEDIUM', 'WEAK'].map(level => {
                const levelDecisions = decisions?.filter(d => d.convictionLevel === level) ?? [];
                const levelApproved = levelDecisions.filter(d => d.state === 'APPROVED').length;
                return (
                  <WinRateRow
                    key={level}
                    label={level}
                    total={levelDecisions.length}
                    won={levelApproved}
                  />
                );
              })}
            </div>
          ) : (
            <EmptyState
              title="No Calibration Data"
              description="Calibration metrics will appear when conviction levels are tracked against outcomes."
            />
          )}
        </div>

        {/* Research Quality */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Research Quality</h3>
          <EmptyState
            title="No Research Quality Data"
            description="Research quality metrics will appear when research is linked to outcomes."
          />
        </div>

        {/* Forecast Quality */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Forecast Quality</h3>
          <EmptyState
            title="No Forecast Data"
            description="Forecast quality metrics will appear when forecasts are tracked against outcomes."
          />
        </div>
      </div>
    </>
  );
}

function WinRateRow({ label, total, won }: { label: string; total: number; won: number }) {
  const rate = total > 0 ? (won / total * 100) : 0;
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-sm font-mono">{won}/{total}</span>
        <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full"
            style={{ width: `${rate}%` }}
          />
        </div>
        <span className="text-sm font-mono w-12 text-right">{rate.toFixed(0)}%</span>
      </div>
    </div>
  );
}
