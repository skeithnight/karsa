// @ts-nocheck
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

import CioDashboardWorkspace from '../page';
import { usePortfolioSummary, usePortfolioExposure } from '../../hooks/portfolio';

vi.mock('../../hooks/portfolio');

describe('CioDashboardWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton when loading', () => {
    vi.mocked(usePortfolioSummary).mockReturnValue({ isLoading: true } as any);
    vi.mocked(usePortfolioExposure).mockReturnValue({ isLoading: true } as any);
    render(<CioDashboardWorkspace />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState when error', () => {
    vi.mocked(usePortfolioSummary).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    vi.mocked(usePortfolioExposure).mockReturnValue({ isLoading: false } as any);
    render(<CioDashboardWorkspace />);
    expect(screen.getByTestId('error-state')).toBeDefined();
  });

  it('renders EmptyState when empty', () => {
    vi.mocked(usePortfolioSummary).mockReturnValue({ data: null, isLoading: false } as any);
    vi.mocked(usePortfolioExposure).mockReturnValue({ data: { sectors: [] }, isLoading: false } as any);
    render(<CioDashboardWorkspace />);
    expect(screen.getAllByTestId('empty-state').length).toBeGreaterThan(0);
  });

  it('renders Primary content when data exists', () => {
    vi.mocked(usePortfolioSummary).mockReturnValue({
      data: { totalAumDisplay: '1B', activeThesesCount: 5, dailyPnlDisplay: '10M', dailyPnlRaw: 10 },
      isLoading: false
    } as any);
    vi.mocked(usePortfolioExposure).mockReturnValue({
      data: { sectors: [{ sector: 'Tech', allocationPctDisplay: '50%' }] },
      isLoading: false
    } as any);
    render(<CioDashboardWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
    expect(screen.queryByTestId("empty-state")).toBeNull();
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
