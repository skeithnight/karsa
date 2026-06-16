// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ThesesWorkspace from '../page';
import { useListTheses } from '../../../hooks/theses';
import { useRouter } from 'next/navigation';

vi.mock('../../../hooks/theses');
vi.mock('next/navigation', () => ({ useRouter: vi.fn() }));

vi.mock('../../../components/grid/DataTable', () => ({
  DataTable: ({ onRowClick, rowData }: any) => (
    <div data-testid="mock-datatable">
      {rowData.map((row: any, i: number) => (
        <button key={i} data-testid={`row-${row.thesisUrn}`} onClick={() => onRowClick(row)}>
          Row {row.thesisUrn}
        </button>
      ))}
    </div>
  )
}));

describe('ThesesWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as any);
    vi.mocked(useListTheses).mockReturnValue({ isLoading: true } as any);
    render(<ThesesWorkspace />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as any);
    vi.mocked(useListTheses).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    render(<ThesesWorkspace />);
    expect(screen.getByTestId('error-state')).toBeDefined();
  });

  it('renders EmptyState', () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as any);
    vi.mocked(useListTheses).mockReturnValue({ data: { data: [] }, isLoading: false } as any);
    render(<ThesesWorkspace />);
    expect(screen.getByTestId('empty-state')).toBeDefined();
  });

  it('renders primary content and navigates on row click', () => {
    const pushMock = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push: pushMock } as any);
    vi.mocked(useListTheses).mockReturnValue({ data: { data: [{ thesisUrn: '1', ticker: 'AAPL', direction: 'LONG', convictionScoreDisplay: '5' }] }, isLoading: false } as any);
    render(<ThesesWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
    
    // Test Navigation
    const rowButton = screen.getByTestId('row-1');
    fireEvent.click(rowButton);
    expect(pushMock).toHaveBeenCalledWith('/theses/1');
  });
});
