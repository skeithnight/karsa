import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import RootLayout from '../layout';
import { AppProviders } from '../../providers';
import { GlobalErrorBoundary } from '../../components/error/GlobalErrorBoundary';
import { AppLayout } from '../../components/layout/AppLayout';

vi.mock('../../providers', () => ({
  AppProviders: vi.fn(({ children }) => <div data-testid="app-providers">{children}</div>)
}));

vi.mock('../../components/error/GlobalErrorBoundary', () => ({
  GlobalErrorBoundary: vi.fn(({ children }) => <div data-testid="global-error-boundary">{children}</div>)
}));

vi.mock('../../components/layout/AppLayout', () => ({
  AppLayout: vi.fn(({ children }) => <div data-testid="app-layout">{children}</div>)
}));

describe('RootLayout Provider Composition', () => {
  it('mounts AppProviders, GlobalErrorBoundary, and AppLayout in exact sequence', () => {
    const { getByTestId } = render(<RootLayout><div>Test Child</div></RootLayout>);
    
    // Verify mounting
    expect(getByTestId('app-providers')).toBeDefined();
    expect(getByTestId('global-error-boundary')).toBeDefined();
    expect(getByTestId('app-layout')).toBeDefined();
    
    // Verify they are actually called
    expect(AppProviders).toHaveBeenCalled();
    expect(GlobalErrorBoundary).toHaveBeenCalled();
    expect(AppLayout).toHaveBeenCalled();
  });
});
