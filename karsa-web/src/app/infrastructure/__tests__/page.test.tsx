// @ts-nocheck

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import InfrastructureWorkspace from '../page';

describe('InfrastructureWorkspace', () => {
  it('renders primary content', () => {
    render(<InfrastructureWorkspace />);
    expect(screen.queryByTestId("empty-state")).toBeNull();
  });
});
