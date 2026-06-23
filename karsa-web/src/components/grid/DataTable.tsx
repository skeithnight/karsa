import React from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

import { LoadingSkeleton } from "../shared/LoadingSkeleton";
import { EmptyState } from "../shared/EmptyState";
import { exportToCsv } from "../../lib/export";

export interface DataTableProps<T> {
  rowData: T[];
  columnDefs: ColDef<T>[];
  isLoading?: boolean;
  onRowClick?: (row: T) => void;
  onSortChanged?: (sort: any) => void;
  onPaginationChanged?: (page: number) => void;
  /** Enable CSV export button */
  exportable?: boolean;
  /** Filename for CSV export */
  exportFilename?: string;
  /** Row height in pixels (default 28 for trading density) */
  rowHeight?: number;
  /** Header row height in pixels (default 32 for trading density) */
  headerHeight?: number;
}

export function DataTable<T>({
  rowData,
  columnDefs,
  isLoading,
  onRowClick,
  onSortChanged,
  onPaginationChanged,
  exportable = false,
  exportFilename = "export",
  rowHeight = 28,
  headerHeight = 32,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="p-4">
        <LoadingSkeleton variant="table" />
      </div>
    );
  }

  if (!rowData || rowData.length === 0) {
    return (
      <EmptyState
        title="No Data"
        description="There are no records to display."
      />
    );
  }

  const handleExport = () => {
    const columns = columnDefs
      .filter(cd => cd.field)
      .map(cd => ({ key: cd.field!, label: cd.headerName ?? cd.field! }));
    exportToCsv(exportFilename, rowData as Record<string, unknown>[], columns);
  };

  return (
    <div>
      {exportable && (
        <div className="flex justify-end mb-2">
          <button
            onClick={handleExport}
            className="text-xs px-3 py-1 border rounded hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            Export CSV
          </button>
        </div>
      )}
      <div className="ag-theme-alpine-dark w-full h-[600px]">
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          rowHeight={rowHeight}
          headerHeight={headerHeight}
          onRowClicked={(e) => {
            if (e.data !== undefined) {
              onRowClick?.(e.data);
            }
          }}
          onSortChanged={onSortChanged}
          onPaginationChanged={(e) => onPaginationChanged?.(e.api.paginationGetCurrentPage())}
          pagination={true}
        />
      </div>
    </div>
  );
}
