'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { usePortfolioExposure } from '../../hooks/portfolio';

export default function PortfolioWorkspace() {
  const { data, isLoading, isError, error, refetch } = usePortfolioExposure();

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Portfolio Workspace" description="Asset allocation and exposure analysis" />
      
      <div className="mt-6 mb-8 h-64 border rounded-xl flex items-center justify-center bg-white dark:bg-slate-900">
        {isLoading ? <LoadingSkeleton variant="card" /> : <span className="text-slate-400">Exposure Chart</span>}
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : (data?.sectors?.length ?? 0) > 0 ? (
        <DataTable rowData={data?.sectors ?? []} columnDefs={[{ field: 'sector' }, { field: 'allocationPctDisplay' }]} />
      ) : (
        <EmptyState title="No Data" description="No portfolio exposure records" />
      )}
    </>
  );
}
