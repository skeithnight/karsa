'use client';

import { useEffect, useRef, useCallback } from 'react';
import { createChart, LineSeries, ColorType, CrosshairMode } from 'lightweight-charts';
import type {
  IChartApi,
  ISeriesApi,
  Time,
  MouseEventParams,
  LineData,
  SeriesType,
} from 'lightweight-charts';

/**
 * TradingViewChart — Sprint-60
 *
 * High-performance equity curve chart using lightweight-charts (TradingView).
 * Replaces the Recharts LineChart for better rendering performance on large datasets.
 *
 * Props:
 *   data       – equity curve points (timestamp ISO, totalEquity, dailyPnl)
 *   benchmark  – optional IHSG benchmark overlay
 *   height     – chart height in px (default 300)
 */

export interface EquityCurvePoint {
  timestamp: string;
  totalEquity: number;
  dailyPnl: number;
}

export interface BenchmarkPoint {
  timestamp: string;
  totalEquity: number;
}

interface TradingViewChartProps {
  data: EquityCurvePoint[];
  benchmark?: BenchmarkPoint[];
  height?: number;
}

/** Transform equity curve points to lightweight-charts line data, sorted ascending. */
function toLineData(points: { timestamp: string; totalEquity: number }[]) {
  return [...points]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map((p) => ({
      time: p.timestamp.split('T')[0] as Time,
      value: p.totalEquity,
    }));
}

/** Format IDR value for tooltip display. */
function formatIdr(value: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/** Format date string for tooltip display. */
function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function TradingViewChart({ data, benchmark, height = 300 }: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const portfolioSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const benchmarkSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Stable crosshair handler that reads from refs
  const handleCrosshairMove = useCallback(
    (param: MouseEventParams<Time>) => {
      const tooltip = tooltipRef.current;
      if (!tooltip) return;

      if (!param.time || !param.point) {
        tooltip.style.display = 'none';
        return;
      }

      // Extract values from seriesData map (LineData has .value)
      const portfolioEntry = portfolioSeriesRef.current
        ? param.seriesData.get(portfolioSeriesRef.current as ISeriesApi<SeriesType, Time>)
        : undefined;
      const portfolioValue = portfolioEntry ? (portfolioEntry as LineData<Time>).value : undefined;

      const benchmarkEntry = benchmarkSeriesRef.current
        ? param.seriesData.get(benchmarkSeriesRef.current as ISeriesApi<SeriesType, Time>)
        : undefined;
      const benchmarkValue = benchmarkEntry ? (benchmarkEntry as LineData<Time>).value : undefined;

      const timeStr = typeof param.time === 'string' ? param.time : String(param.time);

      let html = `<div style="font-weight:600;margin-bottom:4px;">${formatDate(timeStr)}</div>`;
      html += `<div style="color:#60a5fa;">Portfolio: ${portfolioValue != null ? formatIdr(portfolioValue) : '—'}</div>`;
      if (benchmarkValue != null) {
        html += `<div style="color:#f59e0b;">IHSG: ${formatIdr(benchmarkValue)}</div>`;
      }

      tooltip.innerHTML = html;
      tooltip.style.display = 'block';

      // Position tooltip near crosshair but keep within container bounds
      const container = containerRef.current;
      if (container) {
        const rect = container.getBoundingClientRect();
        let left = param.point.x + 16;
        let top = param.point.y - 40;

        // Clamp to container bounds
        if (left + 200 > rect.width) left = param.point.x - 200 - 16;
        if (top < 0) top = 8;

        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
      }
    },
    []
  );

  // Create chart on mount
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(148, 163, 184, 0.4)',
          width: 1,
          style: 2, // Dashed
          labelBackgroundColor: '#1e293b',
        },
        horzLine: {
          color: 'rgba(148, 163, 184, 0.4)',
          width: 1,
          style: 2, // Dashed
          labelBackgroundColor: '#1e293b',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(148, 163, 184, 0.2)',
      },
      timeScale: {
        borderColor: 'rgba(148, 163, 184, 0.2)',
        timeVisible: false,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Portfolio equity line series (primary)
    const portfolioSeries = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 0,
        minMove: 1,
      },
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBackgroundColor: '#3b82f6',
      lastValueVisible: true,
      priceLineVisible: true,
    });
    portfolioSeriesRef.current = portfolioSeries;

    // Benchmark line series (optional IHSG overlay)
    if (benchmark && benchmark.length > 0) {
      const benchmarkSeries = chart.addSeries(LineSeries, {
        color: '#f59e0b',
        lineWidth: 1,
        lineStyle: 2, // Dashed
        priceFormat: {
          type: 'price',
          precision: 0,
          minMove: 1,
        },
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 3,
        crosshairMarkerBackgroundColor: '#f59e0b',
        lastValueVisible: true,
        priceLineVisible: false,
      });
      benchmarkSeriesRef.current = benchmarkSeries;
    }

    // Subscribe to crosshair move
    chart.subscribeCrosshairMove(handleCrosshairMove);

    // Cleanup
    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      chart.remove();
      chartRef.current = null;
      portfolioSeriesRef.current = null;
      benchmarkSeriesRef.current = null;
    };
  }, [handleCrosshairMove]);

  // Update portfolio data when it changes
  useEffect(() => {
    const series = portfolioSeriesRef.current;
    if (!series || !data.length) return;

    const lineData = toLineData(data);
    series.setData(lineData);
  }, [data]);

  // Update benchmark data when it changes
  useEffect(() => {
    const series = benchmarkSeriesRef.current;
    if (!series || !benchmark?.length) return;

    const lineData = toLineData(benchmark);
    series.setData(lineData);
  }, [benchmark]);

  return (
    <div className="relative w-full" style={{ height }}>
      <div ref={containerRef} className="w-full h-full" />
      <div
        ref={tooltipRef}
        className="absolute z-10 pointer-events-none rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-xl"
        style={{ display: 'none' }}
      />
    </div>
  );
}
