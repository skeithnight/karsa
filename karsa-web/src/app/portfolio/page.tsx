'use client';
import React from 'react';
import { PageHeader } from '@/components/shared/PageHeader';
import { DataTable } from '@/components/grid/DataTable';
import SectorBars from '@/components/shared/SectorBars';
import ConglomerateHeatmap from '@/components/shared/ConglomerateHeatmap';
import ConvictionPips from '@/components/shared/ConvictionPips';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorState } from '@/components/shared/ErrorState';
import { EmptyState } from '@/components/shared/EmptyState';
import { useHoldings, useSectorExposure, useConglomerateExposure, useDashboardKpis } from '@/hooks/dashboard';

const POSITION_COLUMNS = [
  { field: 'ticker' as const, headerName: 'Ticker', flex: 1 },
  { field: 'quantity' as const, headerName: 'Qty', flex: 1, type: 'number' as const },
  { field: 'average_cost' as const, headerName: 'Entry', flex: 1, type: 'number' as const },
  { field: 'market_value' as const, headerName: 'MktVal', flex: 1, type: 'number' as const },
  { field: 'exposure_pct' as const, headerName: 'Exposure%', flex: 1, type: 'number' as const },
];

export default function PortfolioPage() {
  const {
    data: holdings,
    isLoading: holdingsLoading,
    isError: holdingsError,
    error: holdingsErrorObj,
    refetch: refetchHoldings,
  } = useHoldings();

  const {
    data: sectorExposure,
    isLoading: sectorLoading,
    isError: sectorError,
    error: sectorErrorObj,
    refetch: refetchSector,
  } = useSectorExposure();

  const {
    data: conglomerateExposure,
    isLoading: conglomerateLoading,
    isError: conglomerateError,
    error: conglomerateErrorObj,
    refetch: refetchConglomerate,
  } = useConglomerateExposure();

  const { data: kpis } = useDashboardKpis();
  const nav = kpis ? parseFloat(kpis.nav.replace(/[^0-9.]/g, '')) || 1 : 1;

  if (holdingsError) return <ErrorState errorMessage={holdingsErrorObj?.message} onRetry={refetchHoldings} />;
  if (sectorError) return <ErrorState errorMessage={sectorErrorObj?.message} onRetry={refetchSector} />;
  if (conglomerateError) return <ErrorState errorMessage={conglomerateErrorObj?.message} onRetry={refetchConglomerate} />;

  return (
    <>
      <PageHeader title="Portfolio" description="Holdings, sector exposure, and conglomerate allocation" />

      {/* Positions Table */}
      <div className="mt-6">
        {holdingsLoading ? (
          <LoadingSkeleton variant="table" />
        ) : (holdings?.length ?? 0) > 0 ? (
          <DataTable
            rowData={holdings ?? []}
            columnDefs={POSITION_COLUMNS}
          />
        ) : (
          <EmptyState title="No Positions" description="No holdings data available." />
        )}
      </div>

      {/* Sector Bars + Conglomerate Heatmap */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-base font-semibold mb-4">Sector Exposure</h2>
          {sectorLoading ? (
            <LoadingSkeleton variant="card" />
          ) : (sectorExposure?.length ?? 0) > 0 ? (
            <SectorBars sectors={(sectorExposure ?? []).map(s => ({ sector: s.sectorName, pctNav: nav > 0 ? (s.netExposureIdr / nav) * 100 : 0 }))} />
          ) : (
            <EmptyState title="No Data" description="No sector exposure data." />
          )}
        </div>

        <div>
          <h2 className="text-base font-semibold mb-4">Conglomerate Heatmap</h2>
          {conglomerateLoading ? (
            <LoadingSkeleton variant="card" />
          ) : (conglomerateExposure?.length ?? 0) > 0 ? (
            <ConglomerateHeatmap conglomerates={(conglomerateExposure ?? []).map(c => ({ name: c.group, exposurePct: c.exposure_pct, limitPct: c.limit_pct, status: c.status }))} />
          ) : (
            <EmptyState title="No Data" description="No conglomerate exposure data." />
          )}
        </div>
      </div>
    </>
  );
}
