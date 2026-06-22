'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { FreshnessIndicator } from '../../components/shared/FreshnessIndicator';
import { useListResearchReports } from '../../hooks/research';

export default function ResearchWorkspace() {
  const { data, isLoading, isError, error, refetch } = useListResearchReports({ limit: 50 });
  const reportCount = data?.data?.length ?? 0;
  const tickers = new Set(data?.data?.map((r: { ticker?: string }) => r.ticker).filter(Boolean) ?? []);
  const analysts = new Set(data?.data?.map((r: { analystId?: string }) => r.analystId).filter(Boolean) ?? []);

  if (isError) return <ErrorState errorMessage={error?.message} onRetry={refetch} />;

  return (
    <>
      <PageHeader title="Research Workspace" description="Market intelligence and signals" />
      <div className="flex justify-end mt-2 mb-4">
        <FreshnessIndicator isLoading={isLoading} />
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Total Reports</div>
          <div className="text-2xl font-mono font-bold">{isLoading ? '...' : reportCount}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Unique Tickers</div>
          <div className="text-2xl font-mono font-bold">{isLoading ? '...' : tickers.size}</div>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 text-center">
          <div className="text-sm text-slate-500">Analysts</div>
          <div className="text-2xl font-mono font-bold">{isLoading ? '...' : analysts.size}</div>
        </div>
      </div>

      <div className="mt-6">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : reportCount > 0 ? (
          <DataTable
            rowData={data?.data ?? []}
            columnDefs={[
              { field: 'ticker', headerName: 'Ticker' },
              { field: 'analystId', headerName: 'Analyst' },
              { field: 'conviction', headerName: 'Conviction' },
              { field: 'publishedAtDisplay', headerName: 'Published' },
            ]}
            exportable={true}
            exportFilename="research-reports"
            onRowClick={(row) => {
              if (row.id) {
                window.location.href = `/research/${row.id}`;
              }
            }}
          />
        ) : (
          <EmptyState title="No Data" description="No research reports found" />
        )}
      </div>
    </>
  );
}
