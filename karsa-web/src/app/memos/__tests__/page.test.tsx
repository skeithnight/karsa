// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import MemosWorkspace from '../page';
import { useListMemos } from '../../../hooks/memos';

vi.mock('../../../hooks/memos');

describe('MemosWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(useListMemos).mockReturnValue({ data: { data: [{ decisionUrn: '1', intent: 'long', timestampDisplay: 'Now' }] }, isLoading: false } as any);
    render(<MemosWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
