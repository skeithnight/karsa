// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import OversightWorkspace from '../page';
import { useGovernancePostMortems } from '../../../hooks/governance';

vi.mock('../../../hooks/governance');

describe('OversightWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(useGovernancePostMortems).mockReturnValue({ data: { data: [{ thesisUrn: '1', failureReason: 'F', policyOverridesDisplay: 'S' }] }, isLoading: false } as any);
    render(<OversightWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
