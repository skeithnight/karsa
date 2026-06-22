/**
 * FreshnessIndicator -- Phase-1
 * Shows how recently data was fetched
 */

'use client';

import React, { useState, useEffect } from 'react';

interface FreshnessIndicatorProps {
  /** ISO timestamp of last data fetch */
  lastFetched?: string | Date | null;
  /** Stale time in milliseconds */
  staleTimeMs?: number;
  /** Whether data is currently loading */
  isLoading?: boolean;
}

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);

  if (diffSec < 10) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return date.toLocaleDateString();
}

export function FreshnessIndicator({
  lastFetched,
  staleTimeMs = 60_000,
  isLoading,
}: FreshnessIndicatorProps) {
  const [, setTick] = useState(0);

  // Re-render every 10s to keep "X ago" current
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 10_000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <span className="text-xs text-slate-400 animate-pulse">
        Updating...
      </span>
    );
  }

  if (!lastFetched) {
    return (
      <span className="text-xs text-slate-400">
        No data
      </span>
    );
  }

  const date = typeof lastFetched === 'string' ? new Date(lastFetched) : lastFetched;
  const isStale = Date.now() - date.getTime() > staleTimeMs;

  return (
    <span
      className={`text-xs ${isStale ? 'text-amber-500' : 'text-slate-400'}`}
      title={`Last updated: ${date.toLocaleString()}`}
    >
      {isStale ? '⚠ ' : ''}
      Updated {formatTimeAgo(date)}
    </span>
  );
}
