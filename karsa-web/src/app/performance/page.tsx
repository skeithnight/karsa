'use client';
import React from 'react';
import { PageHeader } from '@/components/shared/PageHeader';
import { Card } from '@/components/ui/card';
import BrierCalibration from '@/components/shared/BrierCalibration';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorState } from '@/components/shared/ErrorState';
import { EmptyState } from '@/components/shared/EmptyState';
import { usePerformanceKpis, useBrinsonAttribution, useCalibration } from '@/hooks/performance';

interface KpiCardProps {
  label: string;
  value: string | number | undefined;
  suffix?: string;
}

function KpiCard({ label, value, suffix }: KpiCardProps) {
  return (
    <Card className="p-4 flex flex-col items-center justify-center text-center">
      <span className="text-xs text-slate-500 uppercase tracking-wide">{label}</span>
      <span className="mt-1 text-2xl font-bold">
        {value != null ? `${value}${suffix ?? ''}` : '--'}
      </span>
    </Card>
  );
}

export default function PerformancePage() {
  const {
    data: kpis,
    isLoading: kpisLoading,
    isError: kpisError,
    error: kpisErrorObj,
    refetch: refetchKpis,
  } = usePerformanceKpis();

  const {
    data: brinsonData,
    isLoading: brinsonLoading,
    isError: brinsonError,
    error: brinsonErrorObj,
    refetch: refetchBrinson,
  } = useBrinsonAttribution();

  const {
    data: calibrationData,
    isLoading: calibrationLoading,
    isError: calibrationError,
    error: calibrationErrorObj,
    refetch: refetchCalibration,
  } = useCalibration();

  if (kpisError) return <ErrorState errorMessage={kpisErrorObj?.message} onRetry={refetchKpis} />;
  if (brinsonError) return <ErrorState errorMessage={brinsonErrorObj?.message} onRetry={refetchBrinson} />;
  if (calibrationError) return <ErrorState errorMessage={calibrationErrorObj?.message} onRetry={refetchCalibration} />;

  return (
    <>
      <PageHeader title="Performance" description="Attribution, calibration, and key performance indicators" />

      {/* KPI Strip */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpisLoading ? (
          <>
            {Array.from({ length: 6 }).map((_, i) => (
              <LoadingSkeleton key={i} variant="card" />
            ))}
          </>
        ) : (
          <>
            <KpiCard label="YTD Return" value={kpis?.ytdReturnDisplay} />
            <KpiCard label="Selection Alpha" value={kpis?.selectionAlphaDisplay} />
            <KpiCard label="Allocation Alpha" value={kpis?.allocationAlphaDisplay} />
            <KpiCard label="Beta Drag" value={kpis?.betaDragDisplay} />
            <KpiCard label="Brier Score" value={kpis?.brierScoreDisplay} />
            <KpiCard label="Win Rate" value={kpis?.winRateDisplay} />
          </>
        )}
      </div>

      {/* Brinson Attribution + Brier Calibration */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Brinson Attribution Table */}
        <div>
          <h2 className="text-base font-semibold mb-4">Brinson Attribution</h2>
          {brinsonLoading ? (
            <LoadingSkeleton variant="table" />
          ) : (brinsonData?.length ?? 0) > 0 ? (
            <Card className="overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="text-left p-3 font-medium">Sector</th>
                    <th className="text-right p-3 font-medium">Allocation</th>
                    <th className="text-right p-3 font-medium">Selection</th>
                    <th className="text-right p-3 font-medium">Interaction</th>
                    <th className="text-right p-3 font-medium">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {brinsonData!.map((row, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-slate-100 dark:border-slate-800 last:border-0"
                    >
                      <td className="p-3">{row.periodDisplay}</td>
                      <td className="p-3 text-right">{row.allocationDisplay}</td>
                      <td className="p-3 text-right">{row.selectionDisplay}</td>
                      <td className="p-3 text-right">{row.betaDisplay}</td>
                      <td className="p-3 text-right font-medium">{row.totalDisplay}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ) : (
            <EmptyState title="No Data" description="No Brinson attribution data available." />
          )}
        </div>

        {/* Brier Calibration */}
        <div>
          <h2 className="text-base font-semibold mb-4">Brier Calibration</h2>
          {calibrationLoading ? (
            <LoadingSkeleton variant="card" />
          ) : calibrationData != null ? (
            <BrierCalibration
              tiers={calibrationData.map((c) => ({
                tier: c.tier,
                winPct: c.winPctRaw,
                count: c.count,
              }))}
            />
          ) : (
            <EmptyState title="No Data" description="No calibration data available." />
          )}
        </div>
      </div>
    </>
  );
}
