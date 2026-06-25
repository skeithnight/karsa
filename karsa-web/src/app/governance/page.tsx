'use client';
import React from 'react';
import { PageHeader } from '@/components/shared/PageHeader';
import { Card } from '@/components/ui/card';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorState } from '@/components/shared/ErrorState';
import { EmptyState } from '@/components/shared/EmptyState';
import { useMandateChecks, useInfrastructureStatus } from '@/hooks/governance';

const CHECK_STATUS_STYLES: Record<string, string> = {
  PASS: 'text-emerald-600 dark:text-emerald-400',
  FAIL: 'text-red-600 dark:text-red-400',
  WARN: 'text-amber-600 dark:text-amber-400',
};

const INFRA_STATUS_STYLES: Record<string, string> = {
  HEALTHY: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  DEGRADED: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  DOWN: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
};

export default function GovernancePage() {
  const {
    data: mandateChecks,
    isLoading: mandateLoading,
    isError: mandateError,
    error: mandateErrorObj,
    refetch: refetchMandate,
  } = useMandateChecks();

  const {
    data: infraStatus,
    isLoading: infraLoading,
    isError: infraError,
    error: infraErrorObj,
    refetch: refetchInfra,
  } = useInfrastructureStatus();

  if (mandateError) return <ErrorState errorMessage={mandateErrorObj?.message} onRetry={refetchMandate} />;
  if (infraError) return <ErrorState errorMessage={infraErrorObj?.message} onRetry={refetchInfra} />;

  return (
    <>
      <PageHeader title="Governance" description="Mandate compliance and infrastructure health" />

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mandate Compliance */}
        <Card className="p-5">
          <h2 className="text-base font-semibold mb-4">Mandate Compliance</h2>
          {mandateLoading ? (
            <LoadingSkeleton variant="card" />
          ) : (mandateChecks?.length ?? 0) === 0 ? (
            <EmptyState title="No Checks" description="No mandate checks available." />
          ) : (
            <div className="space-y-3">
              {mandateChecks!.map((check, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0"
                >
                  <div>
                    <span className="text-sm font-medium">{check.rule}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 font-mono">{check.value}</span>
                    <span
                      className={`text-sm font-semibold ${
                        CHECK_STATUS_STYLES[check.status.toUpperCase()] ?? 'text-slate-500'
                      }`}
                    >
                      {check.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Infrastructure Status */}
        <Card className="p-5">
          <h2 className="text-base font-semibold mb-4">Infrastructure Status</h2>
          {infraLoading ? (
            <LoadingSkeleton variant="card" />
          ) : (infraStatus?.length ?? 0) === 0 ? (
            <EmptyState title="No Services" description="No infrastructure services found." />
          ) : (
            <div className="space-y-3">
              {infraStatus!.map((svc, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0"
                >
                  <div>
                    <span className="text-sm font-medium">{svc.service}</span>
                    {svc.note && (
                      <p className="text-xs text-slate-500 mt-0.5">{svc.note}</p>
                    )}
                  </div>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      INFRA_STATUS_STYLES[svc.status.toUpperCase()] ?? ''
                    }`}
                  >
                    {svc.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
