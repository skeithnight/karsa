'use client';

interface Sector {
  sector: string;
  pctNav: number;
}

interface SectorBarsProps {
  sectors: Sector[];
}

export default function SectorBars({ sectors }: SectorBarsProps) {
  const maxPct = Math.max(...sectors.map((s) => Math.abs(s.pctNav)), 1);

  return (
    <div className="space-y-2">
      {sectors.map((s) => (
        <div key={s.sector} className="flex items-center gap-3">
          <span className="w-36 shrink-0 text-sm text-gray-300">
            {s.sector}
          </span>
          <div className="h-4 flex-1 overflow-hidden rounded bg-gray-800">
            <div
              className="h-full rounded bg-indigo-500"
              style={{ width: `${(Math.abs(s.pctNav) / maxPct) * 100}%` }}
            />
          </div>
          <span className="w-14 text-right font-mono text-sm text-gray-400">
            {s.pctNav.toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}
