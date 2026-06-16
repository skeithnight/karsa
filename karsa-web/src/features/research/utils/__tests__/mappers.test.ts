// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { mapListResearchReports } from '../mappers';

describe('Research Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapListResearchReports({ data: [{ id: '1', ticker: 'AAPL', analyst_id: 'a1', conviction: 'HIGH', summary: 's', published_at: '2025-01-01' }] });
    expect(res.data.length).toBe(1);
  });
  it('handles missing array fields gracefully', () => {
    const res = mapListResearchReports({} as any);
    expect(res.data).toEqual([]);
  });
  it('handles null array fields gracefully', () => {
    const res = mapListResearchReports({ data: null } as any);
    expect(res.data).toEqual([]);
  });
  it('handles empty collections', () => {
    const res = mapListResearchReports({ data: [] });
    expect(res.data).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const res = mapListResearchReports({ data: [{ id: '1', ticker: 'AAPL', analyst_id: 'a1', conviction: '', summary: '', published_at: '' }] });
    expect(res.data.length).toBe(1);
  });
});
