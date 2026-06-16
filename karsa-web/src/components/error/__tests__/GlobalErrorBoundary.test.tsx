// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GlobalErrorBoundary } from '../GlobalErrorBoundary';

const Bomb = () => { throw new Error('Global crash') };

describe('GlobalErrorBoundary', () => {
  it('catches error and renders fallback', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <GlobalErrorBoundary>
        <Bomb />
      </GlobalErrorBoundary>
    );
    expect(screen.getByTestId("error-state")).toBeDefined();
  });
});
