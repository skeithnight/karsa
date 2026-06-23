/**
 * ConglomerateHeatmap -- Sprint-59
 *
 * CSS Grid treemap visualization of conglomerate group exposures.
 * Tile size is proportional to exposure; color indicates limit status.
 */
'use client';

import React from 'react';
import type { ConglomerateExposureViewModel } from '../../hooks/cio-dashboard/use-conglomerate-exposures';
import { formatCurrency } from '../../lib/formatters/currency';

interface ConglomerateHeatmapProps {
  data: ConglomerateExposureViewModel[];
  isLoading?: boolean;
}

const STATUS_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  OK: {
    bg: 'bg-emerald-50 dark:bg-emerald-950',
    border: 'border-emerald-300 dark:border-emerald-700',
    text: 'text-emerald-700 dark:text-emerald-300',
  },
  WARNING: {
    bg: 'bg-amber-50 dark:bg-amber-950',
    border: 'border-amber-300 dark:border-amber-700',
    text: 'text-amber-700 dark:text-amber-300',
  },
  BREACH: {
    bg: 'bg-red-50 dark:bg-red-950',
    border: 'border-red-400 dark:border-red-700',
    text: 'text-red-700 dark:text-red-300',
  },
};

function statusLabel(status: string): string {
  switch (status) {
    case 'BREACH':
      return 'BREACH';
    case 'WARNING':
      return 'NEAR LIMIT';
    default:
      return 'WITHIN LIMIT';
  }
}

export function ConglomerateHeatmap({ data, isLoading }: ConglomerateHeatmapProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-3 animate-pulse">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="h-28 rounded-lg bg-slate-100 dark:bg-slate-800" />
        ))}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No conglomerate exposure data available
      </div>
    );
  }

  // Sort by exposure descending for visual hierarchy
  const sorted = [...data].sort((a, b) => b.exposurePct - a.exposurePct);
  const maxExposure = Math.max(...sorted.map((d) => d.exposurePct), 0.01);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {sorted.map((item) => {
        const colors = STATUS_COLORS[item.status] || STATUS_COLORS.OK;
        // Scale tile height based on relative exposure (min 100px, max 200px)
        const relativeSize = Math.max(0.4, item.exposurePct / maxExposure);
        const tileHeight = 100 + relativeSize * 100;
        const utilizationPct = item.limitPct > 0
          ? ((item.exposurePct / item.limitPct) * 100).toFixed(0)
          : '0';

        return (
          <div
            key={item.group}
            className={`rounded-lg border-2 p-4 flex flex-col justify-between transition-all hover:shadow-md ${colors.bg} ${colors.border}`}
            style={{ minHeight: `${tileHeight}px` }}
          >
            {/* Header */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-semibold text-sm">{item.group}</h4>
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${colors.text} ${colors.bg}`}
                >
                  {statusLabel(item.status)}
                </span>
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                {item.tickers.join(' / ')}
              </div>
            </div>

            {/* Exposure bar */}
            <div className="mt-auto">
              <div className="flex items-baseline justify-between mb-1">
                <span className="text-lg font-mono font-bold">
                  {item.exposurePct.toFixed(1)}%
                </span>
                <span className="text-xs text-slate-500">
                  / {item.limitPct.toFixed(0)}% limit
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    item.status === 'BREACH'
                      ? 'bg-red-500'
                      : item.status === 'WARNING'
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(100, Number(utilizationPct))}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-400 mt-1">
                {formatCurrency(item.totalExposureIdr, 'IDR')} &middot; {utilizationPct}% utilized
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
