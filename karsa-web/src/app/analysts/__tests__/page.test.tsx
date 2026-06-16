// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import AnalystsWorkspace from '../page';
import { useAnalystsMetrics } from '../../../hooks/analysts';

vi.mock('../../../hooks/analysts');

describe('AnalystsWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(useAnalystsMetrics).mockReturnValue({ data: { data: [{ analystId: 'A1', role: 'W', winRateDisplay: '100%', trustScoreDisplay: '5' }] }, isLoading: false } as any);
    render(<AnalystsWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
