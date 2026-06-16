// @ts-nocheck
import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import { MetricCard } from '../MetricCard';

test('renders MetricCard with title and metric', () => {
  render(<MetricCard title="Total AUM" metric="$10M" />);
  expect(screen.getByText('Total AUM')).toBeTruthy();
  expect(screen.getByText('$10M')).toBeTruthy();
});
