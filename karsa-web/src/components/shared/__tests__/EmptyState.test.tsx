// @ts-nocheck
import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import { EmptyState } from '../EmptyState';

test('renders EmptyState with title and description', () => {
  render(<EmptyState title="No Data" description="Check back later" />);
  expect(screen.getByText('No Data')).toBeTruthy();
  expect(screen.getByText('Check back later')).toBeTruthy();
});
