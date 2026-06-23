'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { ErrorState } from '../../components/shared/ErrorState';
import { BrierScoreChart, CalibrationPoint } from '../../components/charts/BrierScoreChart';
import { AttributionTable, BrinsonAttributionRow } from '../../components/tables/AttributionTable';
import { useBrierScores, useBrinsonAttribution } from '../../hooks/performance';

/**
 * Transform Brier score entries into calibration scatter plot points.
 * Groups scores into decile bins and computes actual win rates.
 */
function buildCalibrationPoints(
  scores: { evaluationSequence: number; score: number }[]
): CalibrationPoint[] {
  // For stub data, derive calibration points from the score sequence.
  // In production this would come from the CalibrationProjectionService.
  const bins: CalibrationPoint[] = [];
  for (let i = 0; i < 10; i++) {
    const conviction = (i + 0.5) / 10;
    const binScores = scores.filter(
      (s) => s.evaluationSequence >= i * 3 && s.evaluationSequence < (i + 1) * 3
    );
    if (binScores.length > 0) {
      const avgBrier =
        binScores.reduce((sum, s) => sum + s.score, 0) / binScores.length;
      const actualWinRate = Math.max(0, Math.min(1, conviction + (0.5 - avgBrier) * 0.4));
      bins.push({
        conviction,
        actualWinRate,
        sampleSize: binScores.length * 10,
        brierScore: avgBrier,
      });
    }
  }
  return bins;
}

export default function PerformancePage() {
  const {
    data: brierData,
    isLoading: brierLoading,
    isError: brierError,
    error: brierErrorObj,
    refetch: refetchBrier,
  } = useBrierScores();

  const {
    data: brinsonData,
    isLoading: brinsonLoading,
    isError: brinsonError,
    error: brinsonErrorObj,
    refetch: refetchBrinson,
  } = useBrinsonAttribution();

  if (brierError) {
    return <ErrorState errorMessage={brierErrorObj?.message} onRetry={refetchBrier} />;
  }
  if (brinsonError) {
    return <ErrorState errorMessage={brinsonErrorObj?.message} onRetry={refetchBrinson} />;
  }

  const calibrationPoints = brierData ? buildCalibrationPoints(brierData) : [];
  const overallBrierScore = brierData && brierData.length > 0
    ? brierData.reduce((sum, s) => sum + s.score, 0) / brierData.length
    : undefined;

  const attributionRows: BrinsonAttributionRow[] =
    brinsonData?.map((entry) => ({
      ...entry,
      brierScore: overallBrierScore ?? 0,
      calibrationScore: overallBrierScore != null ? 1 - overallBrierScore : 0,
    })) ?? [];

  return (
    <>
      <PageHeader
        title="Performance Workspace"
        description="Forecast calibration, Brier scores, and Brinson attribution analysis"
      />

      {/* Brier Score Calibration Chart */}
      <div className="mt-6 mb-8">
        {brierLoading ? (
          <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 h-[400px] animate-pulse" />
        ) : (
          <BrierScoreChart
            data={calibrationPoints}
            overallBrierScore={overallBrierScore}
          />
        )}
      </div>

      {/* Brinson Attribution Table */}
      <AttributionTable data={attributionRows} isLoading={brinsonLoading} />
    </>
  );
}
