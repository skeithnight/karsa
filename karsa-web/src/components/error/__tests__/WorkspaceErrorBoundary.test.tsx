// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkspaceErrorBoundary } from '../WorkspaceErrorBoundary';

const Bomb = () => { throw new Error('Workspace Error: Workspace crash') };

describe('WorkspaceErrorBoundary', () => {
  it('catches error and renders fallback', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <WorkspaceErrorBoundary>
        <Bomb />
      </WorkspaceErrorBoundary>
    );
    expect(screen.getByTestId("error-state")).toBeDefined();
  });
});
