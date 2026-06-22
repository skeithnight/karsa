'use client';
import React from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';

/**
 * Portfolio Holdings Detail
 * Phase-2: Drill-down from portfolio sector allocation
 */
export default function HoldingsPage() {
  return (
    <>
      <PageHeader
        title="Portfolio Holdings"
        description="Individual position details"
      />
      <div className="mt-6">
        <EmptyState
          title="No Holdings Data"
          description="Position-level data will appear here when connected to the portfolio engine."
        />
      </div>
    </>
  );
}
