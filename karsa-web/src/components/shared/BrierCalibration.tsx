'use client';

import { cn } from '@/lib/utils';

interface Tier {
  tier: string;
  winPct: number;
  count: number;
}

interface BrierCalibrationProps {
  tiers: Tier[];
}

const TIER_COLORS: Record<string, string> = {
  STRONG: 'bg-green-500',
  MEDIUM: 'bg-amber-500',
  WEAK: 'bg-red-500',
};

export default function BrierCalibration({ tiers }: BrierCalibrationProps) {
  return (
    <div className="space-y-4">
      {tiers.map((t) => (
        <div key={t.tier} className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-300">{t.tier}</span>
            <span className="font-mono text-sm text-gray-400">
              {t.winPct.toFixed(1)}% ({t.count})
            </span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-gray-800">
            <div
              className={cn(
                'h-full rounded-full',
                TIER_COLORS[t.tier] ?? 'bg-gray-600'
              )}
              style={{ width: `${Math.min(t.winPct, 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
