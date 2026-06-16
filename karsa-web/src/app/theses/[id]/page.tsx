'use client';
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
      <PageHeader title={detail?.ticker || 'Thesis Detail'} description={detail?.thesisUrn || ''} />
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
        <MetricCard title="Ticker" metric={detail?.ticker || '-'} statusIndicator="neutral" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Thesis Summary</h3>
          <p className="text-sm text-slate-600">No summary available in VM.</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Thesis Narrative</h3>
          <p className="text-sm text-slate-600">Primary investment logic goes here.</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Invalidation Criteria</h3>
          <ul className="list-disc pl-4 text-sm text-slate-600">
            {(detail?.invalidationCriteria ?? []).map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      </div>

      <div className="mt-8 border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">Lineage & Related Artifacts</h3>
        <div className="flex space-x-4">
          <button className="px-4 py-2 bg-slate-100 text-slate-800 rounded-md">
            Lineage ({((lineage?.sourceResearchIds?.length ?? 0) + (lineage?.decisionUrns?.length ?? 0) + (lineage?.governanceReviewIds?.length ?? 0))})
          </button>
          <button className="px-4 py-2 bg-slate-100 text-slate-800 rounded-md">Related Research</button>
          <button className="px-4 py-2 bg-slate-100 text-slate-800 rounded-md">Related Memos</button>
        </div>
      </div>
    </>
  );
}
