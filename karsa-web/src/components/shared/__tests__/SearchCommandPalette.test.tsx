// @ts-nocheck

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SearchCommandPalette } from '../SearchCommandPalette';

vi.mock('cmdk', () => ({
  Command: Object.assign(
    ({ children, ...props }: any) => <div data-testid="cmdk-mock" {...props}>{children}</div>,
    {
      Dialog: ({ children }: any) => <div>{children}</div>,
      Input: (props: any) => <input {...props} />,
      List: ({ children }: any) => <div>{children}</div>,
      Empty: ({ children }: any) => <div>{children}</div>,
      Group: ({ children }: any) => <div>{children}</div>,
      Item: ({ children }: any) => <div>{children}</div>,
      Separator: () => <hr />,
    }
  )
}));

vi.mock('../../ui/dialog', () => ({
  Dialog: ({ children }: any) => <div>{children}</div>,
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <div>{children}</div>,
  DialogDescription: ({ children }: any) => <div>{children}</div>,
}));

describe('SearchCommandPalette', () => {
  it('renders properly without results', () => {
    const setIsOpen = vi.fn();
    const setSearchText = vi.fn();
    render(<SearchCommandPalette isOpen={true} setIsOpen={setIsOpen} searchText="" setSearchText={setSearchText} />);
    expect(screen.getByPlaceholderText('Type a command or search...')).toBeDefined();
  });

  it('renders loading state', () => {
    const setIsOpen = vi.fn();
    const setSearchText = vi.fn();
    render(<SearchCommandPalette isOpen={true} setIsOpen={setIsOpen} searchText="app" setSearchText={setSearchText} isLoading={true} />);
    expect(screen.getByText('Searching...')).toBeDefined();
  });

  it('renders error state', () => {
    const setIsOpen = vi.fn();
    const setSearchText = vi.fn();
    render(<SearchCommandPalette isOpen={true} setIsOpen={setIsOpen} searchText="app" setSearchText={setSearchText} isError={true} />);
    expect(screen.getByText('Failed to fetch results.')).toBeDefined();
  });

  it('renders empty state when no results match', () => {
    const setIsOpen = vi.fn();
    const setSearchText = vi.fn();
    render(<SearchCommandPalette isOpen={true} setIsOpen={setIsOpen} searchText="xyz" setSearchText={setSearchText} results={[]} />);
    expect(screen.getByText('No results found.')).toBeDefined();
  });

  it('renders search results correctly', () => {
    const setIsOpen = vi.fn();
    const setSearchText = vi.fn();
    const mockResults = [
      { id: '1', label: 'Apple Inc', subtitle: 'AAPL', type: 'THESIS', route: '/theses/1' }
    ];
    render(<SearchCommandPalette isOpen={true} setIsOpen={setIsOpen} searchText="app" setSearchText={setSearchText} results={mockResults} />);
    
    expect(screen.getByText('Apple Inc')).toBeDefined();
    expect(screen.getByText('AAPL')).toBeDefined();
    expect(screen.getByText('THESIS')).toBeDefined();
  });
});
