'use client';

import { cn } from '@/lib/utils';

interface RiskMetric {
  metric: string;
  current: string;
  limit: string;
  utilizationPct: number;
  status: string;
}

interface RiskPanelProps {
  metrics: RiskMetric[];
}

function statusColor(status: string) {
  switch (status.toLowerCase()) {
    case 'green':
    case 'ok':
    case 'normal':
      return 'bg-green-500';
    case 'amber':
    case 'warning':
    case 'caution':
      return 'bg-amber-500';
    case 'red':
    case 'breach':
    case 'critical':
      return 'bg-red-500';
    default:
      return 'bg-gray-500';
  }
}

function barColor(pct: number) {
  if (pct >= 90) return 'bg-red-500';
  if (pct >= 70) return 'bg-amber-500';
  return 'bg-green-500';
}

export default function RiskPanel({ metrics }: RiskPanelProps) {
  return (
    <div className="space-y-3">
      {metrics.map((m) => (
        <div
          key={m.metric}
          className="flex items-center gap-4 rounded-lg border border-gray-800 bg-gray-900 px-4 py-3"
        >
          <div className="w-40 shrink-0">
            <p className="text-sm font-medium text-gray-300">{m.metric}</p>
          </div>

          <div className="w-24 shrink-0 text-right">
            <p className="font-mono text-sm text-gray-100">{m.current}</p>
          </div>

          <div className="w-16 shrink-0 text-right">
            <p className="text-xs text-gray-500">/ {m.limit}</p>
          </div>

          <div className="flex flex-1 items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-800">
              <div
                className={cn('h-full rounded-full', barColor(m.utilizationPct))}
                style={{ width: `${Math.min(m.utilizationPct, 100)}%` }}
              />
            </div>
            <span className="w-12 text-right font-mono text-xs text-gray-400">
              {m.utilizationPct}%
            </span>
          </div>

          <span
            className={cn('h-2.5 w-2.5 rounded-full', statusColor(m.status))}
          />
        </div>
      ))}
    </div>
  );
}
