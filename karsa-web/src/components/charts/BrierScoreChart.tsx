'use client';

import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ZAxis,
  Cell,
} from 'recharts';

export interface CalibrationPoint {
  /** Predicted probability (conviction) */
  conviction: number;
  /** Actual win rate observed */
  actualWinRate: number;
  /** Number of forecasts in this bin */
  sampleSize: number;
  /** Brier score for this bin */
  brierScore: number;
}

export interface BrierScoreChartProps {
  /** Calibration curve data points */
  data: CalibrationPoint[];
  /** Overall Brier score to display in header */
  overallBrierScore?: number;
  /** Height in pixels (default 400) */
  height?: number;
}

/**
 * Tooltip content for the calibration scatter plot.
 */
function CalibrationTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: CalibrationPoint }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-lg border bg-white dark:bg-slate-900 p-3 shadow-md text-sm">
      <div className="font-semibold mb-1">Calibration Bin</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <span className="text-slate-500">Predicted:</span>
        <span className="font-mono">{(point.conviction * 100).toFixed(0)}%</span>
        <span className="text-slate-500">Actual:</span>
        <span className="font-mono">{(point.actualWinRate * 100).toFixed(1)}%</span>
        <span className="text-slate-500">Samples:</span>
        <span className="font-mono">{point.sampleSize}</span>
        <span className="text-slate-500">Brier:</span>
        <span className="font-mono">{point.brierScore.toFixed(4)}</span>
      </div>
    </div>
  );
}

/**
 * Get color based on distance from perfect calibration (diagonal).
 * Green = well calibrated, amber = moderate, red = poor.
 */
function getCalibrationColor(point: CalibrationPoint): string {
  const distance = Math.abs(point.conviction - point.actualWinRate);
  if (distance < 0.1) return '#22c55e'; // green
  if (distance < 0.25) return '#f59e0b'; // amber
  return '#ef4444'; // red
}

/**
 * BrierScoreChart -- Recharts scatter plot showing predicted conviction
 * vs actual win rate, with a diagonal reference line for perfect calibration.
 *
 * Points on the diagonal indicate perfect calibration. Points above the
 * diagonal are under-confident (actual > predicted). Points below are
 * over-confident (predicted > actual).
 */
export function BrierScoreChart({
  data,
  overallBrierScore,
  height = 400,
}: BrierScoreChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center border rounded-xl bg-white dark:bg-slate-900 text-slate-400"
        style={{ height }}
      >
        No calibration data available
      </div>
    );
  }

  return (
    <div className="border rounded-xl p-4 bg-white dark:bg-slate-900">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Forecast Calibration</h3>
          <p className="text-sm text-slate-500">
            Predicted conviction vs actual win rate
          </p>
        </div>
        {overallBrierScore !== undefined && (
          <div className="text-right">
            <div className="text-sm text-slate-500">Brier Score</div>
            <div className="text-2xl font-mono font-bold">
              {overallBrierScore.toFixed(4)}
            </div>
            <div className="text-xs text-slate-400">
              {overallBrierScore < 0.15
                ? 'Excellent'
                : overallBrierScore < 0.25
                  ? 'Good'
                  : 'Needs improvement'}
            </div>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
          <XAxis
            type="number"
            dataKey="conviction"
            name="Predicted"
            domain={[0, 1]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            label={{
              value: 'Predicted Conviction',
              position: 'insideBottom',
              offset: -10,
              style: { fill: '#94a3b8', fontSize: 12 },
            }}
          />
          <YAxis
            type="number"
            dataKey="actualWinRate"
            name="Actual"
            domain={[0, 1]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            label={{
              value: 'Actual Win Rate',
              angle: -90,
              position: 'insideLeft',
              offset: 10,
              style: { fill: '#94a3b8', fontSize: 12 },
            }}
          />
          <ZAxis
            type="number"
            dataKey="sampleSize"
            range={[40, 200]}
            name="Samples"
          />
          <Tooltip content={<CalibrationTooltip />} />

          {/* Perfect calibration diagonal reference line */}
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: 1, y: 1 },
            ]}
            stroke="#64748b"
            strokeDasharray="6 3"
            strokeWidth={1.5}
            label={{
              value: 'Perfect',
              position: 'insideTopRight',
              style: { fill: '#64748b', fontSize: 11 },
            }}
          />

          <Scatter data={data} shape="circle">
            {data.map((point, index) => (
              <Cell
                key={`cell-${index}`}
                fill={getCalibrationColor(point)}
                fillOpacity={0.8}
                stroke={getCalibrationColor(point)}
                strokeWidth={1}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
