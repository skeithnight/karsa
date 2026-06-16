// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { mapListAnalysts, mapAnalystMetric } from '../mappers';

describe('Analysts Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapListAnalysts({ data: [{ analyst_id: '1', role: 'worker', trust_score: 1, win_rate: 0.8, drawdown: 0.1 }] });
    expect(res.data.length).toBe(1);
    expect(res.data[0].analystId).toBe('1');
    expect(res.data[0].performanceStatus.text).toBe('Outperform');
  });
  it('handles missing array fields gracefully', () => {
    const res = mapListAnalysts({} as any);
    expect(res.data).toEqual([]);
  });
  it('handles null array fields gracefully', () => {
    const res = mapListAnalysts({ data: null } as any);
    expect(res.data).toEqual([]);
  });
  it('handles empty collections', () => {
    const res = mapListAnalysts({ data: [] });
    expect(res.data).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const res = mapListAnalysts({ data: [{ analyst_id: '2', role: 'worker', trust_score: 0, win_rate: 0.2, drawdown: 0 }] });
    expect(res.data[0].performanceStatus.text).toBe('Underperform');
  });
});
