// @ts-nocheck
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { ErrorState } from '../ErrorState';

test('renders ErrorState and handles retry callback', () => {
  const onRetry = vi.fn();
  render(<ErrorState errorMessage="Network failed" onRetry={onRetry} />);
  
  expect(screen.getByText('Network failed')).toBeTruthy();
  
  const retryBtn = screen.getByTestId('error-retry-button');
  fireEvent.click(retryBtn);
  expect(onRetry).toHaveBeenCalledOnce();
});

test('renders fallback display when provided', () => {
  render(<ErrorState errorMessage="Error" fallbackDisplay={<div>Custom Fallback</div>} />);
  expect(screen.getByText('Custom Fallback')).toBeTruthy();
});
