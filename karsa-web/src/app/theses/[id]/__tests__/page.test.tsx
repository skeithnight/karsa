// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import ThesisDetailWorkspace from '../page';
import { useThesisDetail, useThesisLineage } from '../../../../hooks/theses';

vi.mock('../../../../hooks/theses');
vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react')>();
  return { ...actual, use: (p: any) => p };
});

describe('ThesisDetailWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(useThesisDetail).mockReturnValue({ isLoading: true } as any);
    vi.mocked(useThesisLineage).mockReturnValue({ isLoading: true } as any);
    render(<ThesisDetailWorkspace params={{ id: '1' } as any} />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(useThesisDetail).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    vi.mocked(useThesisLineage).mockReturnValue({ isLoading: false } as any);
    render(<ThesisDetailWorkspace params={{ id: '1' } as any} />);
    expect(screen.getByTestId('error-state')).toBeDefined();
  });

  it('renders primary content', () => {
    vi.mocked(useThesisDetail).mockReturnValue({ data: { thesisUrn: '1', ticker: 'AAPL', invalidationCriteria: ['Cr 1'] }, isLoading: false } as any);
    vi.mocked(useThesisLineage).mockReturnValue({ data: { sourceResearchIds: ['r1'], decisionUrns: [], governanceReviewIds: [] }, isLoading: false } as any);
    render(<ThesisDetailWorkspace params={{ id: '1' } as any} />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
