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
            <MetricCard title="Total AUM" value={summary.totalAumDisplay} trend={summary.aumTrendDisplay} />
            <MetricCard title="Active Theses" value={summary.activeThesesDisplay} trend="Neutral" />
            <MetricCard title="Daily P&L" value={summary.dailyPnlDisplay} trend={summary.dailyPnlRaw >= 0 ? 'Positive' : 'Negative'} />
          </>
        ) : (
          <div className="col-span-3"><EmptyState message="No summary data available" /></div>
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
          <EmptyState message="No exposure data available" />
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
        <DataTable data={data.sectors} columns={[{ field: 'sectorName' }, { field: 'allocationDisplay' }]} />
      ) : (
        <EmptyState message="No portfolio exposure records" />
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
        ) : data && data.reports.length > 0 ? (
          <DataTable data={data.reports} columns={[{ field: 'title' }, { field: 'authorName' }, { field: 'publishedAtDisplay' }]} />
        ) : (
          <EmptyState message="No research reports found" />
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
        ) : data && data.items.length > 0 ? (
          <DataTable 
            data={data.items} 
            columns={[{ field: 'title' }, { field: 'statusDisplay' }, { field: 'convictionDisplay' }]} 
            onRowClick={(row: any) => router.push(`/theses/${row.id}`)}
          />
        ) : (
          <EmptyState message="No active theses found" />
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
      <PageHeader title={detail?.title || 'Thesis Detail'} description={detail?.statusDisplay || ''} />
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
        <MetricCard title="Conviction" value={detail?.convictionDisplay || '-'} trend="Neutral" />
        <MetricCard title="Risk Profile" value={detail?.riskDisplay || '-'} trend="Neutral" />
        <MetricCard title="Horizon" value={detail?.horizonDisplay || '-'} trend="Neutral" />
        <MetricCard title="Created" value={detail?.createdAtDisplay || '-'} trend="Neutral" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Thesis Summary</h3>
          <p className="text-sm text-slate-600">{detail?.summary || 'No summary available.'}</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Thesis Narrative</h3>
          <p className="text-sm text-slate-600">Primary investment logic goes here.</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Metadata</h3>
          <p className="text-sm text-slate-600">Tags, Authors, and Context.</p>
        </div>
      </div>

      <div className="mt-8 border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">Lineage & Related Artifacts</h3>
        <div className="flex space-x-4">
          <button className="px-4 py-2 bg-slate-100 text-slate-800 rounded-md">Lineage ({lineage?.events.length || 0})</button>
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
        ) : data && data.items.length > 0 ? (
          <DataTable data={data.items} columns={[{ field: 'title' }, { field: 'decisionDateDisplay' }]} />
        ) : (
          <EmptyState message="No memos available" />
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
            <MetricCard title="Total Analysts" value={data?.metrics.length.toString() || '0'} trend="Neutral" />
            <MetricCard title="Active Coverage" value="Coverage Health" trend="Positive" />
          </>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : data && data.metrics.length > 0 ? (
        <DataTable data={data.metrics} columns={[{ field: 'analystName' }, { field: 'coverageDisplay' }]} />
      ) : (
        <EmptyState message="No analyst metrics found" />
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
      ) : data && data.attributions.length > 0 ? (
        <DataTable data={data.attributions} columns={[{ field: 'fundName' }, { field: 'contributionDisplay' }]} />
      ) : (
        <EmptyState message="No attribution data available" />
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
        ) : data && data.records.length > 0 ? (
          <DataTable data={data.records} columns={[{ field: 'title' }, { field: 'dateDisplay' }, { field: 'severityDisplay' }]} />
        ) : (
          <EmptyState message="No oversight records found" />
        )}
      </div>
    </>
  );
}
"""

# 10. Infrastructure
files['src/app/infrastructure/page.tsx'] = """'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';

export default function InfrastructureWorkspace() {
  return (
    <>
      <PageHeader title="Infrastructure Workspace" description="Platform Operations and Limits" />
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Provider Status</h3>
          <span className="text-2xl font-bold text-green-600">Operational</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Capability Status</h3>
          <span className="text-2xl font-bold text-green-600">Active</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Queue Status</h3>
          <span className="text-2xl font-bold text-slate-800 dark:text-slate-200">0 pending</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Worker Status</h3>
          <span className="text-2xl font-bold text-green-600">Healthy</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32 lg:col-span-2">
          <h3 className="font-semibold text-slate-600">System Health</h3>
          <span className="text-sm text-slate-500 mt-2">All platform services are running nominally within configured limits.</span>
        </div>
      </div>
    </>
  );
}
"""

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("Generated workspace pages")
