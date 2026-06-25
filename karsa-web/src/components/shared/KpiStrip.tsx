'use client';

import { cn } from '@/lib/utils';

interface Kpi {
  label: string;
  value: string;
  subtitle?: string;
  positive?: boolean;
}

interface KpiStripProps {
  kpis: Kpi[];
}

export default function KpiStrip({ kpis }: KpiStripProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-lg border border-gray-800 bg-gray-900 p-4"
        >
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
            {kpi.label}
          </p>
          <p
            className={cn(
              'mt-1 font-mono text-2xl font-bold',
              kpi.positive === true
                ? 'text-green-400'
                : kpi.positive === false
                  ? 'text-red-400'
                  : 'text-gray-100'
            )}
          >
            {kpi.value}
          </p>
          {kpi.subtitle && (
            <p className="mt-1 text-xs text-gray-500">{kpi.subtitle}</p>
          )}
        </div>
      ))}
    </div>
  );
}
