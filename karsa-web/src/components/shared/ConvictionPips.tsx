'use client';

import { cn } from '@/lib/utils';

interface ConvictionPipsProps {
  level: number;
  max?: number;
}

export default function ConvictionPips({ level, max = 5 }: ConvictionPipsProps) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: max }, (_, i) => (
        <span
          key={i}
          className={cn(
            'inline-block h-2.5 w-2.5 rounded-full',
            i < level ? 'bg-indigo-500' : 'bg-gray-700'
          )}
        />
      ))}
    </div>
  );
}
