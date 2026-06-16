'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { useListResearchReports } from '../../hooks/research';

export default function ResearchWorkspace() {
  const { data, isLoading, isError, error, refetch } = useListResearchReports({ limit: 50 });

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Research Workspace" description="Market intelligence and signals" />
      <div className="mt-6">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (data?.data?.length ?? 0) > 0 ? (
          <DataTable rowData={data?.data ?? []} columnDefs={[{ field: 'ticker' }, { field: 'analystId' }, { field: 'publishedAtDisplay' }]} />
        ) : (
          <EmptyState title="No Data" description="No research reports found" />
        )}
      </div>
    </>
  );
}
