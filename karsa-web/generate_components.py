import os

base_dir = "src/components"

files = {
    "grid/DataTable.tsx": """import React from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

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
    return <div className="p-4">Loading grid...</div>;
  }

  if (!rowData || rowData.length === 0) {
    return <div className="p-4">No data available</div>;
  }

  return (
    <div className="ag-theme-alpine w-full h-[600px]">
      <AgGridReact
        rowData={rowData}
        columnDefs={columnDefs}
        onRowClicked={(e) => onRowClick?.(e.data)}
        onSortChanged={onSortChanged}
        onPaginationChanged={(e) => onPaginationChanged?.(e.api.paginationGetCurrentPage())}
        pagination={true}
      />
    </div>
  );
}
""",
    "shared/MetricCard.tsx": """import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

export interface MetricCardProps {
  title: string;
  metric: string;
  subtext?: string;
  delta?: number;
  statusIndicator?: "positive" | "negative" | "neutral";
}

export function MetricCard({ title, metric, subtext, delta, statusIndicator = "neutral" }: MetricCardProps) {
  return (
    <Card data-testid="metric-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{metric}</div>
        {(subtext || delta !== undefined) && (
          <p className="text-xs text-muted-foreground flex items-center mt-1">
            {statusIndicator === "positive" && <ArrowUp className="w-3 h-3 text-green-500 mr-1" />}
            {statusIndicator === "negative" && <ArrowDown className="w-3 h-3 text-red-500 mr-1" />}
            {statusIndicator === "neutral" && <Minus className="w-3 h-3 text-gray-500 mr-1" />}
            {delta !== undefined && <span className="mr-1">{delta}%</span>}
            {subtext}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
""",
    "shared/PageHeader.tsx": """import React from "react";

export interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: string[];
  actionSlot?: React.ReactNode;
}

export function PageHeader({ title, description, breadcrumbs, actionSlot }: PageHeaderProps) {
  return (
    <div className="flex justify-between items-center pb-4 border-b mb-6">
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="text-xs text-muted-foreground mb-1">
            {breadcrumbs.join(" / ")}
          </nav>
        )}
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actionSlot && <div>{actionSlot}</div>}
    </div>
  );
}
""",
    "shared/EmptyState.tsx": """import React from "react";
import { AlertCircle } from "lucide-react";

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center" data-testid="empty-state">
      <div className="mb-4 text-muted-foreground">
        {icon || <AlertCircle className="w-12 h-12" />}
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground mt-2 max-w-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
""",
    "shared/ErrorState.tsx": """import React from "react";

export interface ErrorStateProps {
  errorMessage: string;
  onRetry?: () => void;
  fallbackDisplay?: React.ReactNode;
}

export function ErrorState({ errorMessage, onRetry, fallbackDisplay }: ErrorStateProps) {
  if (fallbackDisplay) {
    return <div data-testid="error-state-fallback">{fallbackDisplay}</div>;
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 border border-red-200 bg-red-50 text-red-800 rounded-md" data-testid="error-state">
      <h3 className="text-lg font-semibold mb-2">An error occurred</h3>
      <p className="text-sm mb-4">{errorMessage}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
          data-testid="error-retry-button"
        >
          Retry
        </button>
      )}
    </div>
  );
}
""",
    "shared/LoadingSkeleton.tsx": """import React from "react";
import { Skeleton } from "../ui/skeleton";

export interface LoadingSkeletonProps {
  variant: "card" | "table" | "page";
}

export function LoadingSkeleton({ variant }: LoadingSkeletonProps) {
  if (variant === "card") {
    return (
      <div className="p-4 border rounded-xl space-y-3">
        <Skeleton className="h-4 w-[100px]" />
        <Skeleton className="h-8 w-[200px]" />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <Skeleton className="h-12 w-1/3" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
""",
    "shared/SearchCommandPalette.tsx": """import React, { useEffect } from "react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "../ui/command";

export interface SearchCommandPaletteProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  searchText: string;
  setSearchText: (text: string) => void;
}

export function SearchCommandPalette({
  isOpen,
  setIsOpen,
  searchText,
  setSearchText,
}: SearchCommandPaletteProps) {
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen(!isOpen);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [isOpen, setIsOpen]);

  return (
    <CommandDialog open={isOpen} onOpenChange={setIsOpen}>
      <CommandInput
        placeholder="Type a command or search..."
        value={searchText}
        onValueChange={setSearchText}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Suggestions">
          <CommandItem>Example Item</CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
"""
}

test_files = {
    "vitest.config.ts": """import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
""",
    "src/components/shared/__tests__/MetricCard.test.tsx": """import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import { MetricCard } from '../MetricCard';

test('renders MetricCard with title and metric', () => {
  render(<MetricCard title="Total AUM" metric="$10M" />);
  expect(screen.getByText('Total AUM')).toBeTruthy();
  expect(screen.getByText('$10M')).toBeTruthy();
});
""",
    "src/components/shared/__tests__/EmptyState.test.tsx": """import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import { EmptyState } from '../EmptyState';

test('renders EmptyState with title and description', () => {
  render(<EmptyState title="No Data" description="Check back later" />);
  expect(screen.getByText('No Data')).toBeTruthy();
  expect(screen.getByText('Check back later')).toBeTruthy();
});
""",
    "src/components/shared/__tests__/ErrorState.test.tsx": """import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { ErrorState } from '../ErrorState';

test('renders ErrorState and handles retry callback', () => {
  const onRetry = vi.fn();
  render(<ErrorState errorMessage="Network failed" onRetry={onRetry} />);
  
  expect(screen.getByText('Network failed')).toBeTruthy();
  
  const retryBtn = screen.getByTestId('error-retry-button');
  fireEvent.click(retryBtn);
  expect(onRetry).toHaveBeenCalledOnce();
});

test('renders fallback display when provided', () => {
  render(<ErrorState errorMessage="Error" fallbackDisplay={<div>Custom Fallback</div>} />);
  expect(screen.getByText('Custom Fallback')).toBeTruthy();
});
"""
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

for path, content in test_files.items():
    full_path = os.path.join(path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("Component files and tests generated successfully.")
