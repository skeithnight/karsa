'use client';

import { cn } from '@/lib/utils';

interface Conglomerate {
  name: string;
  exposurePct: number;
  limitPct: number;
  status: string;
}

interface ConglomerateHeatmapProps {
  conglomerates: Conglomerate[];
}

function statusClasses(status: string) {
  switch (status.toLowerCase()) {
    case 'green':
    case 'ok':
    case 'normal':
      return 'border-green-500/40 bg-green-500/10 text-green-400';
    case 'amber':
    case 'warning':
    case 'caution':
      return 'border-amber-500/40 bg-amber-500/10 text-amber-400';
    case 'red':
    case 'breach':
    case 'critical':
      return 'border-red-500/40 bg-red-500/10 text-red-400';
    default:
      return 'border-gray-700 bg-gray-800 text-gray-400';
  }
}

export default function ConglomerateHeatmap({
  conglomerates,
}: ConglomerateHeatmapProps) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {conglomerates.map((c) => (
        <div
          key={c.name}
          className={cn(
            'rounded-lg border p-4',
            statusClasses(c.status)
          )}
        >
          <p className="truncate text-sm font-medium">{c.name}</p>
          <p className="mt-1 font-mono text-lg font-bold">
            {c.exposurePct.toFixed(1)}%
          </p>
          <p className="text-xs opacity-70">Limit: {c.limitPct.toFixed(1)}%</p>
        </div>
      ))}
    </div>
  );
}
