// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { mapPerformanceAttribution } from '../mappers';

describe('Performance Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapPerformanceAttribution({ data: [{ date: '2025-01-01', selection_return: 0.1, allocation_return: 0.1, beta_return: 0.1 }] });
    expect(res.data.length).toBe(1);
  });
  it('handles missing array fields gracefully', () => {
    const res = mapPerformanceAttribution({} as any);
    expect(res.data).toEqual([]);
  });
  it('handles null array fields gracefully', () => {
    const res = mapPerformanceAttribution({ data: null } as any);
    expect(res.data).toEqual([]);
  });
  it('handles empty collections', () => {
    const res = mapPerformanceAttribution({ data: [] });
    expect(res.data).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const res = mapPerformanceAttribution({ data: [{ date: '', selection_return: 0, allocation_return: 0, beta_return: 0 }] });
    expect(res.data[0].selectionReturnDisplay).toBe('0.00%');
  });
});
