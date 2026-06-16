import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { AppProviders } from '../index';
import { QueryProvider } from '../query-provider';
import { ThemeProvider } from '../theme-provider';

vi.mock('../query-provider', () => ({
  QueryProvider: vi.fn(({ children }) => <div data-testid="query-provider">{children}</div>)
}));

vi.mock('../theme-provider', () => ({
  ThemeProvider: vi.fn(({ children }) => <div data-testid="theme-provider">{children}</div>)
}));

describe('AppProviders Composition', () => {
  it('mounts QueryProvider and ThemeProvider', () => {
    const { getByTestId } = render(<AppProviders><div>Test Child</div></AppProviders>);
    
    expect(getByTestId('query-provider')).toBeDefined();
    expect(getByTestId('theme-provider')).toBeDefined();
    
    expect(QueryProvider).toHaveBeenCalled();
    expect(ThemeProvider).toHaveBeenCalled();
  });
});
