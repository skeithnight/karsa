'use client';

import React, { useMemo } from 'react';
import { ColDef } from 'ag-grid-community';
import { DataTable } from '../grid/DataTable';

export interface BrinsonAttributionRow {
  period: string;
  selectionPct: number;
  allocationPct: number;
  betaPct: number;
  residualPct: number;
  totalReturnPct: number;
  winRate: number;
  modelAccuracy: number;
  brierScore: number;
  calibrationScore: number;
}

export interface AttributionTableProps {
  /** Brinson attribution data rows */
  data: BrinsonAttributionRow[];
  /** Loading state */
  isLoading?: boolean;
}

/** Format a number as percentage string */
function pctFormatter(params: { value?: number }): string {
  if (params.value == null) return '--';
  const sign = params.value > 0 ? '+' : '';
  return `${sign}${params.value.toFixed(2)}%`;
}

/** Format a number as a ratio (0-1) to percentage */
function ratioFormatter(params: { value?: number }): string {
  if (params.value == null) return '--';
  return `${(params.value * 100).toFixed(1)}%`;
}

/** Cell class rules for positive/negative values */
const positiveNegativeClassRules = {
  'text-green-500': (params: { value?: number }) => (params.value ?? 0) > 0,
  'text-red-500': (params: { value?: number }) => (params.value ?? 0) < 0,
};

/**
 * Column definitions for the Brinson attribution table.
 * Defined at module level to avoid re-creation on each render.
 */
const columnDefs: ColDef<BrinsonAttributionRow>[] = [
  {
    field: 'period',
    headerName: 'Period',
    width: 100,
    pinned: 'left' as const,
    cellClass: 'font-semibold',
  },
  {
    field: 'selectionPct',
    headerName: 'Selection',
    valueFormatter: pctFormatter,
    cellClassRules: positiveNegativeClassRules,
  },
  {
    field: 'allocationPct',
    headerName: 'Allocation',
    valueFormatter: pctFormatter,
    cellClassRules: positiveNegativeClassRules,
  },
  {
    field: 'betaPct',
    headerName: 'Beta',
    valueFormatter: pctFormatter,
    cellClassRules: positiveNegativeClassRules,
  },
  {
    field: 'residualPct',
    headerName: 'Residual',
    valueFormatter: pctFormatter,
    cellClassRules: positiveNegativeClassRules,
  },
  {
    field: 'totalReturnPct',
    headerName: 'Total Return',
    valueFormatter: pctFormatter,
    cellClassRules: positiveNegativeClassRules,
    cellClass: 'font-bold',
  },
  {
    field: 'winRate',
    headerName: 'Win Rate',
    valueFormatter: ratioFormatter,
  },
  {
    field: 'modelAccuracy',
    headerName: 'Model Accuracy',
    valueFormatter: ratioFormatter,
  },
  {
    field: 'brierScore',
    headerName: 'Brier Score',
    valueFormatter: (params: { value?: number }) =>
      params.value != null ? params.value.toFixed(4) : '--',
  },
  {
    field: 'calibrationScore',
    headerName: 'Calibration',
    valueFormatter: ratioFormatter,
  },
];

/**
 * AttributionTable -- AG Grid table showing Brinson attribution breakdown.
 *
 * Displays selection, allocation, beta, and residual return components
 * per period, along with win rate, model accuracy, Brier score, and
 * calibration score.
 */
export function AttributionTable({ data, isLoading }: AttributionTableProps) {
  return (
    <div className="border rounded-xl p-4 bg-white dark:bg-slate-900">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Brinson Attribution</h3>
        <p className="text-sm text-slate-500">
          Performance decomposition: selection, allocation, beta, residual
        </p>
      </div>
      <DataTable
        rowData={data}
        columnDefs={columnDefs}
        isLoading={isLoading}
        exportable={true}
        exportFilename="brinson-attribution"
      />
    </div>
  );
}
