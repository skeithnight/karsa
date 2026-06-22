'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { useInvestmentDecisions } from '../../hooks/cio-dashboard';

/**
 * Investment Decisions Page
 * Phase-3: End-to-end investment decision tracking
 */
export default function InvestmentsPage() {
  const { data: decisions, isLoading, isError, error, refetch } = useInvestmentDecisions();

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader
        title="Investment Decisions"
        description="End-to-end investment decision lifecycle tracking"
      />
      <div className="mt-6">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (decisions?.length ?? 0) > 0 ? (
          <DataTable
            rowData={decisions ?? []}
            columnDefs={[
              { field: 'ticker', headerName: 'Ticker' },
              { field: 'state', headerName: 'Status' },
              { field: 'convictionLevel', headerName: 'Conviction' },
              { field: 'memoDecision', headerName: 'Decision' },
              { field: 'entryPrice', headerName: 'Entry Price' },
              { field: 'exitTarget', headerName: 'Target' },
              { field: 'analystCount', headerName: 'Analysts' },
              { field: 'debateCount', headerName: 'Debates' },
              { field: 'decisionDate', headerName: 'Date' },
            ]}
            exportable={true}
            exportFilename="investment-decisions"
          />
        ) : (
          <EmptyState
            title="No Investment Decisions"
            description="Investment decisions will appear here when the workflow engine produces them."
          />
        )}
      </div>
    </>
  );
}
