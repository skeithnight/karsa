// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { mapListInvestmentOversight } from '../mappers';

describe('Governance Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapListInvestmentOversight({ data: [{ id: '1', thesis_urn: 't1', failure_reason: 'f', policy_overrides: true, timestamp: '2025-01-01' }] });
    expect(res.data.length).toBe(1);
  });
  it('handles missing array fields gracefully', () => {
    const res = mapListInvestmentOversight({} as any);
    expect(res.data).toEqual([]);
  });
  it('handles null array fields gracefully', () => {
    const res = mapListInvestmentOversight({ data: null } as any);
    expect(res.data).toEqual([]);
  });
  it('handles empty collections', () => {
    const res = mapListInvestmentOversight({ data: [] });
    expect(res.data).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const res = mapListInvestmentOversight({ data: [{ id: '1', thesis_urn: 't1', failure_reason: 'f', policy_overrides: false, timestamp: '' }] });
    expect(res.data[0].policyOverridesDisplay).toBe('Standard');
  });
});
