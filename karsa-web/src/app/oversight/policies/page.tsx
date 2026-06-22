'use client';
import React from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { EmptyState } from '../../../components/shared/EmptyState';

/**
 * Governance Policies
 * Active governance rules and mandate limits
 */
export default function PoliciesPage() {
  const sectorLimits = [
    { sector: 'Finance', limit: '30%', current: '0%', utilization: 0 },
    { sector: 'Energy', limit: '20%', current: '0%', utilization: 0 },
    { sector: 'Consumer', limit: '25%', current: '0%', utilization: 0 },
    { sector: 'Technology', limit: '15%', current: '0%', utilization: 0 },
    { sector: 'Infrastructure', limit: '15%', current: '0%', utilization: 0 },
  ];

  const positionLimits = [
    { rule: 'Single Stock', limit: '3%', description: 'Maximum allocation to any single stock' },
    { rule: 'Top 5 Concentration', limit: '60%', description: 'Top 5 holdings as % of portfolio' },
    { rule: 'Top 10 Concentration', limit: '80%', description: 'Top 10 holdings as % of portfolio' },
    { rule: 'Cash Minimum', limit: '2%', description: 'Minimum cash reserve' },
  ];

  const riskLimits = [
    { metric: 'Annual Volatility', limit: '22%', description: 'Maximum annualized volatility' },
    { metric: 'Max Drawdown', limit: '15%', description: 'Maximum peak-to-trough decline' },
    { metric: 'Beta Range', limit: '0.8-1.3', description: 'Portfolio beta vs IHSG' },
    { metric: 'Correlation', limit: '<0.7', description: 'Maximum pairwise sector correlation' },
  ];

  return (
    <>
      <PageHeader
        title="Governance Policies"
        description="Active mandate rules and investment limits"
      />

      {/* Sector Limits */}
      <div className="border rounded-xl p-6 bg-white dark:bg-slate-900 mt-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Sector Allocation Limits</h3>
        <div className="space-y-3">
          {sectorLimits.map(item => (
            <div key={item.sector} className="flex items-center justify-between">
              <span className="text-sm font-medium w-32">{item.sector}</span>
              <div className="flex items-center gap-2 flex-1">
                <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${(item.utilization) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-mono w-16 text-right">{item.current}</span>
                <span className="text-xs text-slate-400 w-12">/ {item.limit}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Position Limits */}
      <div className="border rounded-xl p-6 bg-white dark:bg-slate-900 mb-6">
        <h3 className="text-lg font-semibold mb-4">Position Limits</h3>
        <div className="space-y-3">
          {positionLimits.map(item => (
            <div key={item.rule} className="flex items-center justify-between border-b pb-2">
              <div>
                <span className="text-sm font-medium">{item.rule}</span>
                <div className="text-xs text-slate-500">{item.description}</div>
              </div>
              <span className="text-sm font-mono font-bold">{item.limit}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Limits */}
      <div className="border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Risk Limits</h3>
        <div className="space-y-3">
          {riskLimits.map(item => (
            <div key={item.metric} className="flex items-center justify-between border-b pb-2">
              <div>
                <span className="text-sm font-medium">{item.metric}</span>
                <div className="text-xs text-slate-500">{item.description}</div>
              </div>
              <span className="text-sm font-mono font-bold">{item.limit}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
