'use client';

import React from 'react';
import { PageHeader } from '../components/shared/PageHeader';
import { MetricCard } from '../components/shared/MetricCard';
import { LoadingSkeleton } from '../components/shared/LoadingSkeleton';
import { ErrorState } from '../components/shared/ErrorState';
import { EmptyState } from '../components/shared/EmptyState';
import { usePortfolioSummary, usePortfolioExposure } from '../hooks/portfolio';

export default function CioDashboardWorkspace() {
  const { data: summary, isLoading: isLoadingSummary, isError: isErrorSummary, error: summaryError, refetch: refetchSummary } = usePortfolioSummary();
  const { data: exposure, isLoading: isLoadingExposure, isError: isErrorExposure, error: exposureError, refetch: refetchExposure } = usePortfolioExposure();

  if (isErrorSummary) return <ErrorState errorMessage={summaryError?.message} onRetry={refetchSummary} />;
  if (isErrorExposure) return <ErrorState errorMessage={exposureError?.message} onRetry={refetchExposure} />;

  return (
    <>
      <PageHeader title="CIO Dashboard" description="Executive macro overview" />
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {isLoadingSummary ? (
          <>
            <LoadingSkeleton variant="card" />
            <LoadingSkeleton variant="card" />
            <LoadingSkeleton variant="card" />
          </>
        ) : summary ? (
          <>
            <MetricCard title="Total AUM" metric={summary.totalAumDisplay} statusIndicator="neutral" />
            <MetricCard title="Active Theses" metric={summary.activeThesesCount.toString()} statusIndicator="neutral" />
            <MetricCard title="Daily P&L" metric={summary.dailyPnlDisplay} statusIndicator={summary.dailyPnlRaw >= 0 ? 'positive' : 'negative'} />
          </>
        ) : (
          <div className="col-span-3"><EmptyState title="No Data" description="No summary data available" /></div>
        )}
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-bold mb-4">Sector Exposure</h2>
        {isLoadingExposure ? (
          <LoadingSkeleton variant="card" />
        ) : (exposure?.sectors?.length ?? 0) > 0 ? (
          <div className="h-64 border rounded-xl flex items-center justify-center bg-white dark:bg-slate-900">
            {/* Chart primitive placeholder */}
            <span className="text-slate-400">Exposure Chart (Recharts)</span>
          </div>
        ) : (
          <EmptyState title="No Data" description="No exposure data available" />
        )}
      </div>
    </>
  );
}
