'use client';
import React from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';

/**
 * Thesis Comparison View
 * Phase-7: Side-by-side thesis comparison
 */
export default function ThesisComparePage() {
  return (
    <>
      <PageHeader
        title="Compare Theses"
        description="Side-by-side comparison of investment theses"
      />
      <div className="mt-6">
        <EmptyState
          title="No Theses Selected"
          description="Select theses from the Theses page to compare them side-by-side."
        />
      </div>
    </>
  );
}
