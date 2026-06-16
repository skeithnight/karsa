'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { MetricCard } from '../../components/shared/MetricCard';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { useAnalystsMetrics } from '../../hooks/analysts';

export default function AnalystsWorkspace() {
  const { data, isLoading, isError, error, refetch } = useAnalystsMetrics();

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Analysts Workspace" description="Worker performance and output" />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 mb-8">
        {isLoading ? (
          <>
            <LoadingSkeleton variant="card" />
            <LoadingSkeleton variant="card" />
          </>
        ) : (
          <>
            <MetricCard title="Total Analysts" metric={(data?.data?.length ?? 0).toString()} statusIndicator="neutral" />
            <MetricCard title="Active Coverage" metric="Coverage Health" statusIndicator="positive" />
          </>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : (data?.data?.length ?? 0) > 0 ? (
        <DataTable rowData={data?.data ?? []} columnDefs={[{ field: 'analystId' }, { field: 'role' }, { field: 'winRateDisplay' }, { field: 'trustScoreDisplay' }]} />
      ) : (
        <EmptyState title="No Data" description="No analyst metrics found" />
      )}
    </>
  );
}
