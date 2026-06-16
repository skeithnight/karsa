// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import ResearchWorkspace from '../page';
import { useListResearchReports } from '../../../hooks/research';

vi.mock('../../../hooks/research');

describe('ResearchWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ isLoading: true } as any);
    render(<ResearchWorkspace />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    render(<ResearchWorkspace />);
    expect(screen.getByTestId('error-state')).toBeDefined();
  });

  it('renders EmptyState', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ data: { data: [] }, isLoading: false } as any);
    render(<ResearchWorkspace />);
    expect(screen.getByTestId('empty-state')).toBeDefined();
  });

  it('renders primary content', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ data: { data: [{ ticker: 'AAPL', analystId: 'A1', publishedAtDisplay: 'Now' }] }, isLoading: false } as any);
    render(<ResearchWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
