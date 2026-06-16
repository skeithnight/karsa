import React from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

import { LoadingSkeleton } from "../shared/LoadingSkeleton";
import { EmptyState } from "../shared/EmptyState";

export interface DataTableProps<T> {
  rowData: T[];
  columnDefs: ColDef<T>[];
  isLoading?: boolean;
  onRowClick?: (row: T) => void;
  onSortChanged?: (sort: any) => void;
  onPaginationChanged?: (page: number) => void;
}

export function DataTable<T>({
  rowData,
  columnDefs,
  isLoading,
  onRowClick,
  onSortChanged,
  onPaginationChanged,
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

  return (
    <div className="ag-theme-alpine w-full h-[600px]">
      <AgGridReact
        rowData={rowData}
        columnDefs={columnDefs}
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
  );
}
