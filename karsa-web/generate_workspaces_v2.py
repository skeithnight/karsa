import os

files = {}

# 1. CIO Dashboard
files['src/app/page.tsx'] = """import React from 'react';
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
            <MetricCard title="Total AUM" metric={summary.totalAum} statusIndicator="neutral" />
            <MetricCard title="Active Theses" metric={summary.activeThesesCount.toString()} statusIndicator="neutral" />
            <MetricCard title="Daily P&L" metric={summary.dailyPnl} statusIndicator={summary.dailyPnlRaw >= 0 ? 'positive' : 'negative'} />
          </>
        ) : (
          <div className="col-span-3"><EmptyState title="No Data" description="No summary data available" /></div>
        )}
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-bold mb-4">Sector Exposure</h2>
        {isLoadingExposure ? (
          <LoadingSkeleton variant="card" />
        ) : exposure && exposure.sectors.length > 0 ? (
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
"""

# 2. Portfolio
files['src/app/portfolio/page.tsx'] = """'use client';
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
      ) : data && data.sectors.length > 0 ? (
        <DataTable rowData={data.sectors} columnDefs={[{ field: 'sectorName' }, { field: 'allocationPercentage' }]} />
      ) : (
        <EmptyState title="No Data" description="No portfolio exposure records" />
      )}
    </>
  );
}
"""

# 3. Research
files['src/app/research/page.tsx'] = """'use client';
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
        ) : data && data.length > 0 ? (
          <DataTable rowData={data} columnDefs={[{ field: 'title' }, { field: 'authorName' }, { field: 'publishedAt' }]} />
        ) : (
          <EmptyState title="No Data" description="No research reports found" />
        )}
      </div>
    </>
  );
}
"""

# 4. Theses
files['src/app/theses/page.tsx'] = """'use client';
import React from 'react';
import { useRouter } from 'next/navigation';
import { PageHeader } from '../../components/shared/PageHeader';
import { DataTable } from '../../components/grid/DataTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { useListTheses } from '../../hooks/theses';

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
        ) : data && data.length > 0 ? (
          <DataTable 
            rowData={data} 
            columnDefs={[{ field: 'title' }, { field: 'status' }, { field: 'conviction' }]} 
            onRowClick={(row: any) => router.push(`/theses/${row.id}`)}
          />
        ) : (
          <EmptyState title="No Data" description="No active theses found" />
        )}
      </div>
    </>
  );
}
"""

# 5. Thesis Detail
files['src/app/theses/[id]/page.tsx'] = """'use client';
import React, { use } from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { MetricCard } from '../../../components/shared/MetricCard';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../../components/shared/ErrorState';
import { useThesisDetail, useThesisLineage } from '../../../hooks/theses';

export function generateStaticParams() {
  return [{ id: '1' }];
}

export default function ThesisDetailWorkspace({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const { id } = resolvedParams;
  const { data: detail, isLoading: isLoadingDetail, isError: isErrorDetail, error: detailError, refetch: refetchDetail } = useThesisDetail(id);
  const { data: lineage, isLoading: isLoadingLineage, isError: isErrorLineage, error: lineageError, refetch: refetchLineage } = useThesisLineage(id);

  if (isErrorDetail) return <ErrorState errorMessage={detailError?.message} onRetry={refetchDetail} />;
  if (isErrorLineage) return <ErrorState errorMessage={lineageError?.message} onRetry={refetchLineage} />;

  if (isLoadingDetail || isLoadingLineage) {
    return (
      <>
        <PageHeader title="Loading Thesis..." description="Retrieving deep conviction logic" />
        <LoadingSkeleton variant="page" />
      </>
    );
  }

  return (
    <>
      <PageHeader title={detail?.title || 'Thesis Detail'} description={detail?.status || ''} />
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
        <MetricCard title="Conviction" metric={detail?.conviction || '-'} statusIndicator="neutral" />
        <MetricCard title="Risk Profile" metric={detail?.riskProfile || '-'} statusIndicator="neutral" />
        <MetricCard title="Horizon" metric={detail?.horizon || '-'} statusIndicator="neutral" />
        <MetricCard title="Created At" metric={detail?.createdAt || '-'} statusIndicator="neutral" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Thesis Summary</h3>
          <p className="text-sm text-slate-600">{detail?.description || 'No summary available.'}</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Thesis Narrative</h3>
          <p className="text-sm text-slate-600">Primary investment logic goes here.</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Metadata</h3>
          <p className="text-sm text-slate-600">Tags: {detail?.tags.join(', ')}</p>
        </div>
      </div>

      <div className="mt-8 border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">Lineage & Related Artifacts</h3>
        <div className="flex space-x-4">
          <button className="px-4 py-2 bg-slate-100 text-slate-800 rounded-md">Lineage ({lineage?.length || 0})</button>
          <button className="px-4 py-2 bg-slate-100 text-slate-800 rounded-md">Related Research</button>
          <button className="px-4 py-2 bg-slate-100 text-slate-800 rounded-md">Related Memos</button>
        </div>
      </div>
    </>
  );
}
"""

# 6. Memos
files['src/app/memos/page.tsx'] = """'use client';
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
        ) : data && data.length > 0 ? (
          <DataTable rowData={data} columnDefs={[{ field: 'title' }, { field: 'decisionDate' }]} />
        ) : (
          <EmptyState title="No Data" description="No memos available" />
        )}
      </div>
    </>
  );
}
"""

# 7. Analysts
files['src/app/analysts/page.tsx'] = """'use client';
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
            <MetricCard title="Total Analysts" metric={data?.length.toString() || '0'} statusIndicator="neutral" />
            <MetricCard title="Active Coverage" metric="Coverage Health" statusIndicator="positive" />
          </>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : data && data.length > 0 ? (
        <DataTable rowData={data} columnDefs={[{ field: 'analystName' }, { field: 'hitRate' }]} />
      ) : (
        <EmptyState title="No Data" description="No analyst metrics found" />
      )}
    </>
  );
}
"""

# 8. Performance
files['src/app/performance/page.tsx'] = """'use client';
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
      ) : data && data.length > 0 ? (
        <DataTable rowData={data} columnDefs={[{ field: 'fundName' }, { field: 'totalAttribution' }]} />
      ) : (
        <EmptyState title="No Data" description="No attribution data available" />
      )}
    </>
  );
}
"""

# 9. Oversight
files['src/app/oversight/page.tsx'] = """'use client';
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
        ) : data && data.length > 0 ? (
          <DataTable rowData={data} columnDefs={[{ field: 'title' }, { field: 'date' }, { field: 'severity' }]} />
        ) : (
          <EmptyState title="No Data" description="No oversight records found" />
        )}
      </div>
    </>
  );
}
"""

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("Generated workspace pages v2")
