/**
 * Stale Data Banner — Sprint-60
 *
 * Prominent warning when data feed is interrupted.
 * AMBER for STALE (>5min), RED pulsing for HALTED (>15min).
 * Critical safety component for IDX trading.
 */
'use client';

import React from 'react';

interface StaleDataBannerProps {
  state: 'FRESH' | 'STALE' | 'HALTED' | string;
  lastBarTime?: string | null;
}

export function StaleDataBanner({ state, lastBarTime }: StaleDataBannerProps) {
  if (state === 'FRESH' || !state) {
    return null;
  }

  if (state === 'HALTED') {
    return (
      <div className="bg-red-600 text-white text-center py-3 font-bold text-lg animate-pulse sticky top-0 z-50">
        <span className="inline-flex items-center gap-2">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          ⚠️ STALE DATA — TRADING HALTED ⚠️
        </span>
        {lastBarTime && (
          <div className="text-sm font-normal mt-1">
            Last data: {new Date(lastBarTime).toLocaleTimeString('id-ID')}
          </div>
        )}
      </div>
    );
  }

  if (state === 'STALE') {
    return (
      <div className="bg-amber-500 text-white text-center py-2 font-semibold sticky top-0 z-50">
        <span className="inline-flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          ⚠️ Data feed degraded — updates may be delayed
        </span>
        {lastBarTime && (
          <div className="text-sm font-normal mt-1">
            Last data: {new Date(lastBarTime).toLocaleTimeString('id-ID')}
          </div>
        )}
      </div>
    );
  }

  return null;
}
