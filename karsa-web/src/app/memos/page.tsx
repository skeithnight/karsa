'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { useListMemos } from '../../hooks/memos';

export default function MemosWorkspace() {
  const { data, isLoading, isError, error, refetch } = useListMemos({ pagination: { page: 1, size: 50 } });

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Memos Workspace" description="Formalized investment decisions" />
      <div className="mt-6">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (data?.data?.length ?? 0) > 0 ? (
          <DataTable rowData={data?.data ?? []} columnDefs={[{ field: 'decisionUrn' }, { field: 'intent' }, { field: 'timestampDisplay' }]} />
        ) : (
          <EmptyState title="No Data" description="No memos available" />
        )}
      </div>
    </>
  );
}
