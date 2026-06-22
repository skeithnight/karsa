'use client';
import React from 'react';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';

/**
 * Post-Mortem Detail
 * Phase-2: Drill-down from oversight governance list
 */
export default function PostMortemDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  return (
    <>
      <PageHeader
        title={`Post-Mortem: ${id}`}
        description="Governance failure analysis and root cause"
      />
      <div className="mt-6">
        <EmptyState
          title="Post-Mortem Detail"
          description="Detailed post-mortem analysis will appear here when connected to the governance engine."
        />
      </div>
    </>
  );
}
