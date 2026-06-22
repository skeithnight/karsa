'use client';
import React from 'react';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';

/**
 * Research Report Detail
 * Phase-5: Research-to-outcome linkage
 */
export default function ResearchDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  return (
    <>
      <PageHeader
        title={`Research: ${id}`}
        description="Research report with linked outcomes and decisions"
      />
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Research Content */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Research Report</h3>
          <EmptyState
            title="No Report Content"
            description="Research content will appear when connected to the research service."
          />
        </div>

        {/* Linked Decisions */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Linked Decisions</h3>
          <EmptyState
            title="No Linked Decisions"
            description="Decisions influenced by this research will appear here."
          />
        </div>

        {/* Outcome Tracking */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-4">Outcome Tracking</h3>
          <EmptyState
            title="No Outcome Data"
            description="Realized returns from decisions based on this research will appear here."
          />
        </div>
      </div>
    </>
  );
}
