'use client';
import React from 'react';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';

/**
 * Investment Decision Detail
 * Phase-3: Decision detail with analyst scores and debate
 */
export default function InvestmentDecisionDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  return (
    <>
      <PageHeader
        title={`Decision: ${id}`}
        description="Investment decision detail with analyst scores, debate, and memo"
      />
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Analyst Scores */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Analyst Scores</h3>
          <EmptyState
            title="No Analyst Data"
            description="Analyst scores will appear when connected to the workflow engine."
          />
        </div>

        {/* Debate */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Bull/Bear Debate</h3>
          <EmptyState
            title="No Debate Data"
            description="Debate memos will appear when connected to the workflow engine."
          />
        </div>

        {/* Decision Memo */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-4">Decision Memo</h3>
          <EmptyState
            title="No Memo"
            description="Investment memo will appear when the decision is finalized."
          />
        </div>
      </div>
    </>
  );
}
