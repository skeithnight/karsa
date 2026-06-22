'use client';
import React from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { usePortfolioHoldings } from '../../../hooks/cio-dashboard';

/**
 * Portfolio Holdings Detail
 * Phase-2: Drill-down from portfolio sector allocation
 */
export default function HoldingsPage() {
  const { data: holdings, isLoading } = usePortfolioHoldings();

  return (
    <>
      <PageHeader
        title="Portfolio Holdings"
        description="Individual position details from portfolio engine"
      />
      <div className="mt-6">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (holdings?.length ?? 0) > 0 ? (
          <div className="border rounded-xl overflow-hidden bg-white dark:bg-slate-900">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-slate-50 dark:bg-slate-800">
                  <th className="text-left p-3 text-sm font-semibold">Ticker</th>
                  <th className="text-right p-3 text-sm font-semibold">Quantity</th>
                  <th className="text-right p-3 text-sm font-semibold">Avg Cost</th>
                  <th className="text-right p-3 text-sm font-semibold">Market Value</th>
                  <th className="text-right p-3 text-sm font-semibold">Exposure %</th>
                </tr>
              </thead>
              <tbody>
                {holdings!.map((h, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800">
                    <td className="p-3 font-mono font-semibold">{String(h.ticker)}</td>
                    <td className="p-3 text-right font-mono">{Number(h.quantity).toLocaleString()}</td>
                    <td className="p-3 text-right font-mono">{Number(h.average_cost).toLocaleString()}</td>
                    <td className="p-3 text-right font-mono">{Number(h.market_value).toLocaleString()}</td>
                    <td className="p-3 text-right font-mono">{Number(h.exposure_pct).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No Holdings Data"
            description="Position-level data will appear here when connected to the portfolio engine."
          />
        )}
      </div>
    </>
  );
}
