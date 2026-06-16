'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { useGovernancePostMortems } from '../../hooks/governance';

export default function OversightWorkspace() {
  const { data, isLoading, isError, error, refetch } = useGovernancePostMortems({ limit: 50 });

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Oversight Workspace" description="Governance and post-mortem review" />
      <div className="mt-6">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (data?.data?.length ?? 0) > 0 ? (
          <DataTable rowData={data?.data ?? []} columnDefs={[{ field: 'thesisUrn' }, { field: 'failureReason' }, { field: 'policyOverridesDisplay' }]} />
        ) : (
          <EmptyState title="No Data" description="No oversight records found" />
        )}
      </div>
    </>
  );
}
