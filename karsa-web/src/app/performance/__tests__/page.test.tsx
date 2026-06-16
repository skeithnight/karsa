// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import PerformanceWorkspace from '../page';
import { usePerformanceAttribution } from '../../../hooks/performance';

vi.mock('../../../hooks/performance');

describe('PerformanceWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(usePerformanceAttribution).mockReturnValue({ data: { data: [{ dateDisplay: 'Jan 1', selectionReturnDisplay: '1%', allocationReturnDisplay: '2%' }] }, isLoading: false } as any);
    render(<PerformanceWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
