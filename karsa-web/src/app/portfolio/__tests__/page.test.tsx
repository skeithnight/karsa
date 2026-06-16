// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import PortfolioWorkspace from '../page';
import { usePortfolioExposure } from '../../../hooks/portfolio';

vi.mock('../../../hooks/portfolio');

describe('PortfolioWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ isLoading: true } as any);
    render(<PortfolioWorkspace />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    render(<PortfolioWorkspace />);
    expect(screen.getByTestId('error-state')).toBeDefined();
  });

  it('renders EmptyState', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ data: { sectors: [] }, isLoading: false } as any);
    render(<PortfolioWorkspace />);
    expect(screen.getByTestId('empty-state')).toBeDefined();
  });

  it('renders primary content', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ data: { sectors: [{ sector: 'Tech', allocationPctDisplay: '50%' }] }, isLoading: false } as any);
    render(<PortfolioWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
