// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { mapSearchResponse } from '../mappers';

describe('Search Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapSearchResponse({ results: [{ id: '1', type: 'THESIS', title: 't', snippet: 's', url: 'u' }] });
    expect(res.results.length).toBe(1);
  });
  it('handles missing array fields gracefully', () => {
    const res = mapSearchResponse({} as any);
    expect(res.results).toEqual([]);
  });
  it('handles null array fields gracefully', () => {
    const res = mapSearchResponse({ results: null } as any);
    expect(res.results).toEqual([]);
  });
  it('handles empty collections', () => {
    const res = mapSearchResponse({ results: [] });
    expect(res.results).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const res = mapSearchResponse({ results: [{ id: '', type: '', title: '', snippet: '', url: '' }] });
    expect(res.results.length).toBe(1);
  });
});
