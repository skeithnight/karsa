'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { usePerformanceAttribution } from '../../hooks/performance';

export default function PerformanceWorkspace() {
  const { data, isLoading, isError, error, refetch } = usePerformanceAttribution({ start_date: '2025-01-01', end_date: '2025-12-31' });

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Performance Workspace" description="Return attribution and alpha analysis" />
      
      <div className="mt-6 mb-8 h-64 border rounded-xl flex items-center justify-center bg-white dark:bg-slate-900">
        {isLoading ? <LoadingSkeleton variant="card" /> : <span className="text-slate-400">Attribution Chart (Recharts)</span>}
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : (data?.data?.length ?? 0) > 0 ? (
        <DataTable rowData={data?.data ?? []} columnDefs={[{ field: 'dateDisplay' }, { field: 'selectionReturnDisplay' }, { field: 'allocationReturnDisplay' }]} />
      ) : (
        <EmptyState title="No Data" description="No attribution data available" />
      )}
    </>
  );
}
