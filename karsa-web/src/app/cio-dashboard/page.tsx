'use client';
import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../components/shared/ErrorState';
import { EmptyState } from '../../components/shared/EmptyState';
import { FreshnessIndicator } from '../../components/shared/FreshnessIndicator';
import {
  usePortfolioSummary,
  useRiskTrafficLight,
  useTodayDecisions,
} from '../../hooks/cio-dashboard';
import type {
  RiskTrafficLightViewModel,
  TodayDecisionViewModel,
} from '../../features/cio-dashboard/types/viewmodels';

/** Tier 1: Executive Summary — 5-second comprehension */
export default function CioDashboardPage() {
  const {
    data: portfolio,
    isLoading: loadingPortfolio,
    isError: errorPortfolio,
    error: portfolioError,
    refetch: refetchPortfolio,
  } = usePortfolioSummary();

  const {
    data: risks,
    isLoading: loadingRisks,
  } = useRiskTrafficLight();

  const {
    data: decisions,
    isLoading: loadingDecisions,
  } = useTodayDecisions();

  if (errorPortfolio) {
    return (
      <ErrorState
        errorMessage={portfolioError?.message}
        onRetry={refetchPortfolio}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="CIO Dashboard"
        description="Executive summary — portfolio, risk, today's decisions"
      />
      <div className="flex justify-end mt-2 mb-4">
        <FreshnessIndicator
          lastFetched={portfolio?.last_updated}
          isLoading={loadingPortfolio}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Portfolio Status Card */}
        <div className="lg:col-span-2 border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Portfolio Status</h3>
          {loadingPortfolio ? (
            <LoadingSkeleton variant="card" />
          ) : portfolio ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="NAV" value={portfolio.nav} />
              <MetricCard label="WTD" value={portfolio.navChangeWtd} />
              <MetricCard label="YTD" value={portfolio.navChangeYtd} />
              <MetricCard label="Sharpe" value={String(portfolio.sharpeRatio)} />
              <MetricCard label="Max DD" value={portfolio.maxDrawdownYtd} />
              <MetricCard label="Holdings" value={String(portfolio.activeHoldings)} />
              <MetricCard label="Cash" value={portfolio.cashPct} />
            </div>
          ) : (
            <EmptyState title="No Data" description="Portfolio data unavailable" />
          )}
        </div>

        {/* Risk Traffic Light */}
        <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
          <h3 className="text-lg font-semibold mb-4">Risk Traffic Light</h3>
          {loadingRisks ? (
            <LoadingSkeleton variant="card" />
          ) : (risks?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              {risks!.map((risk, i) => (
                <RiskRow key={i} risk={risk} />
              ))}
            </div>
          ) : (
            <EmptyState title="No Risk Data" description="Risk metrics unavailable" />
          )}
        </div>
      </div>

      {/* Today's Decisions */}
      <div className="mt-6 border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Today&apos;s Decisions</h3>
        {loadingDecisions ? (
          <LoadingSkeleton variant="table" />
        ) : (decisions?.length ?? 0) > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {decisions!.map((decision, i) => (
              <DecisionCard key={i} decision={decision} />
            ))}
          </div>
        ) : (
          <EmptyState title="No Decisions" description="No decisions today" />
        )}
      </div>
    </>
  );
}

// --- Sub-components ---

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="text-xl font-mono font-semibold">{value}</div>
    </div>
  );
}

function RiskRow({ risk }: { risk: RiskTrafficLightViewModel }) {
  const colorMap = {
    GREEN: 'bg-emerald-500',
    AMBER: 'bg-amber-500',
    RED: 'bg-red-500',
  };
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm">{risk.metric}</span>
      <div className="flex items-center gap-2">
        <span className="text-sm font-mono">{risk.current}</span>
        <div
          className={`w-3 h-3 rounded-full ${colorMap[risk.status]}`}
          title={`${risk.utilizationPct}% of limit`}
        />
      </div>
    </div>
  );
}

function DecisionCard({ decision }: { decision: TodayDecisionViewModel }) {
  const actionColors = {
    BUY: 'text-emerald-600',
    SELL: 'text-red-600',
    HOLD: 'text-slate-600',
    ALERT: 'text-amber-600',
    MONITOR: 'text-blue-600',
  };
  const handleClick = () => {
    if (decision.memoId) {
      window.location.href = `/memos/${decision.memoId}`;
    }
  };
  return (
    <div
      className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${decision.memoId ? 'cursor-pointer' : ''}`}
      onClick={handleClick}
      role={decision.memoId ? 'button' : undefined}
      tabIndex={decision.memoId ? 0 : undefined}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold">{decision.ticker}</span>
        <span className={`text-sm font-mono ${actionColors[decision.action]}`}>
          {decision.action}
        </span>
      </div>
      {decision.conviction && (
        <div className="text-xs text-slate-500 mb-1">
          Conviction: {decision.conviction}
        </div>
      )}
      {decision.targetPrice && (
        <div className="text-xs text-slate-500 mb-1">
          Target: {decision.targetPrice}
        </div>
      )}
      <p className="text-sm text-slate-700 dark:text-slate-300 mt-2">
        {decision.summary}
      </p>
      {decision.memoId && (
        <div className="text-xs text-blue-500 mt-2">
          View Memo →
        </div>
      )}
    </div>
  );
}
