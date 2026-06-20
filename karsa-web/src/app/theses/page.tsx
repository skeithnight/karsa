'use client';
import React from 'react';
import { useRouter } from 'next/navigation';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { useListTheses } from '../../hooks/theses';
import { ThesisVM } from '../../features/theses/types/viewmodels';
import { ThesisGrid } from '../../features/thesis/components/ThesisGrid';

export default function ThesesWorkspace() {
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } = useListTheses({ pagination: { page: 1, size: 50 } });

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Theses Workspace" description="Active investment conviction tracking" />
      <div className="mt-6">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (data?.data?.length ?? 0) > 0 ? (
          <ThesisGrid data={data?.data ?? []} />
        ) : (
          <EmptyState title="No Data" description="No active theses found" />
        )}
      </div>
    </>
  );
}
