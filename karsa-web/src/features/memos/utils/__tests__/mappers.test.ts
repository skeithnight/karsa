// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { mapListInvestmentMemos } from '../mappers';

describe('Memos Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapListInvestmentMemos({ data: [{ decision_urn: '1', thesis_urn: '2', intent: 'long', pep_signature: 'sig', timestamp: '2025-01-01' }], pagination: { total_pages: 1, total_elements: 1 } });
    expect(res.data.length).toBe(1);
  });
  it('handles missing array fields gracefully', () => {
    const res = mapListInvestmentMemos({ pagination: {} } as any);
    expect(res.data).toEqual([]);
    expect(res.totalPages).toBe(1);
  });
  it('handles null array fields gracefully', () => {
    const res = mapListInvestmentMemos({ data: null, pagination: null } as any);
    expect(res.data).toEqual([]);
    expect(res.totalPages).toBe(1);
  });
  it('handles empty collections', () => {
    const res = mapListInvestmentMemos({ data: [], pagination: { total_pages: 0, total_elements: 0 } });
    expect(res.data).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const res = mapListInvestmentMemos({ data: [{ decision_urn: '1', thesis_urn: '2', intent: '', pep_signature: '', timestamp: '' }], pagination: { total_pages: 1, total_elements: 1 } });
    expect(res.data[0].intent).toBe('');
  });
});
