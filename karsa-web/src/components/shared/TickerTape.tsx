'use client';

import { cn } from '@/lib/utils';

interface TickerItem {
  label: string;
  value: string;
  change: string;
  positive: boolean;
}

interface TickerTapeProps {
  items: TickerItem[];
}

export default function TickerTape({ items }: TickerTapeProps) {
  return (
    <div className="overflow-x-auto border-b border-gray-800 bg-gray-900/60">
      <div className="flex gap-6 px-4 py-2">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex shrink-0 items-center gap-3 text-sm"
          >
            <span className="font-medium text-gray-300">{item.label}</span>
            <span className="font-mono text-gray-100">{item.value}</span>
            <span
              className={cn(
                'font-mono text-xs',
                item.positive ? 'text-green-400' : 'text-red-400'
              )}
            >
              {item.change}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
