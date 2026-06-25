'use client';

import React from 'react';
import { PageHeader } from '../components/shared/PageHeader';
import KpiStrip from '../components/shared/KpiStrip';
import RiskPanel from '../components/shared/RiskPanel';
import { LoadingSkeleton } from '../components/shared/LoadingSkeleton';
import { ErrorState } from '../components/shared/ErrorState';
import { EmptyState } from '../components/shared/EmptyState';
import { useDashboardKpis, useRiskTrafficLight, useHoldings } from '../hooks/dashboard';

export default function DashboardPage() {
  const { data: kpis, isLoading: kpisLoading, error: kpisError } = useDashboardKpis();
  const { data: riskMetrics, isLoading: riskLoading } = useRiskTrafficLight();
  const { data: holdings, isLoading: holdingsLoading, error: holdingsError } = useHoldings();

  if (kpisError) return <ErrorState errorMessage="Failed to load dashboard data" />;
  if (holdingsError) return <ErrorState errorMessage="Failed to load holdings" />;

  const kpiItems = kpis ? [
    { label: 'NAV', value: kpis.nav, subtitle: 'portfolio value' },
    { label: 'Daily PnL', value: kpis.dailyPnl, subtitle: kpis.dailyPnlPct, positive: !kpis.dailyPnl.includes('-') },
    { label: 'YTD Alpha', value: kpis.ytdAlpha, subtitle: 'vs IHSG', positive: !kpis.ytdAlpha.includes('-') },
    { label: 'Sharpe', value: kpis.sharpe.toString(), subtitle: 'rolling 12m' },
    { label: 'Max DD', value: kpis.maxDD, subtitle: 'limit -15%', positive: false },
    { label: 'Cash', value: kpis.cash, subtitle: 'idle' },
  ] : [];

  return (
    <>
      <PageHeader title="Dashboard" description="Executive overview" />

      <div className="mt-6">
        {kpisLoading ? <LoadingSkeleton variant="card" /> : <KpiStrip kpis={kpiItems} />}
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-base font-semibold mb-3">Open Positions</h2>
          {holdingsLoading ? (
            <LoadingSkeleton variant="card" />
          ) : (holdings?.length ?? 0) === 0 ? (
            <EmptyState title="No Positions" description="No open positions found." />
          ) : (
            <div className="bg-card border border-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Ticker</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground uppercase">Qty</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground uppercase">Entry</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground uppercase">Mkt Val</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground uppercase">Exposure</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings?.map((h) => (
                    <tr key={h.ticker} className="border-b border-border last:border-0">
                      <td className="px-3 py-2 font-medium">{h.ticker}</td>
                      <td className="px-3 py-2 text-right font-mono">{h.quantity.toLocaleString()}</td>
                      <td className="px-3 py-2 text-right font-mono">{h.average_cost.toLocaleString()}</td>
                      <td className="px-3 py-2 text-right font-mono">{h.market_value.toLocaleString()}</td>
                      <td className="px-3 py-2 text-right font-mono">{h.exposure_pct.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div>
          <h2 className="text-base font-semibold mb-3">Risk Monitor</h2>
          {riskLoading ? <LoadingSkeleton variant="card" /> : (
            <RiskPanel metrics={riskMetrics ?? []} />
          )}
        </div>
      </div>
    </>
  );
}
