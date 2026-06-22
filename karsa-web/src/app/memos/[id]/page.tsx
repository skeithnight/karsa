'use client';
import React from 'react';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';

/**
 * Investment Memo Detail
 * Phase-4: Realized return tracking and feedback loop
 */
export default function MemoDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  return (
    <>
      <PageHeader
        title={`Memo: ${id}`}
        description="Investment memo with realized return tracking"
      />
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Memo Content */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Investment Thesis</h3>
          <EmptyState
            title="No Memo Content"
            description="Memo content will appear when connected to the memo service."
          />
        </div>

        {/* Realized Return */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Realized Return</h3>
          <EmptyState
            title="No Return Data"
            description="Realized returns will appear when positions are closed."
          />
        </div>

        {/* Target vs Actual */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-4">Target vs Actual</h3>
          <EmptyState
            title="No Comparison Data"
            description="Target vs actual comparison will appear when realized returns are tracked."
          />
        </div>
      </div>
    </>
  );
}
