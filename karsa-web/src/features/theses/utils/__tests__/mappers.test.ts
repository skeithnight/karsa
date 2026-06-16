// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { mapListTheses, mapThesisDetail, mapThesisLineage } from '../mappers';

describe('Theses Mappers', () => {
  it('handles valid DTO', () => {
    const list = mapListTheses({ data: [{ thesis_urn: '1', ticker: 'AAPL', direction: 'LONG', state: 'ACTIVE', conviction_score: 5, expected_horizon_days: 30 }], pagination: { total_pages: 1, total_elements: 1 } });
    expect(list.data.length).toBe(1);
    const detail = mapThesisDetail({ thesis_urn: '1', ticker: 'AAPL', invalidation_criteria: ['a'] });
    expect(detail.invalidationCriteria).toEqual(['a']);
    const lineage = mapThesisLineage({ source_research_ids: ['a'], decision_urns: ['b'], governance_review_ids: ['c'] });
    expect(lineage.sourceResearchIds).toEqual(['a']);
  });
  it('handles missing array fields gracefully', () => {
    const list = mapListTheses({ pagination: {} } as any);
    expect(list.data).toEqual([]);
    const detail = mapThesisDetail({} as any);
    expect(detail.invalidationCriteria).toEqual([]);
    const lineage = mapThesisLineage({} as any);
    expect(lineage.sourceResearchIds).toEqual([]);
  });
  it('handles null array fields gracefully', () => {
    const detail = mapThesisDetail({ invalidation_criteria: null } as any);
    expect(detail.invalidationCriteria).toEqual([]);
  });
  it('handles empty collections', () => {
    const detail = mapThesisDetail({ thesis_urn: '1', ticker: 'AAPL', invalidation_criteria: [] });
    expect(detail.invalidationCriteria).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const list = mapListTheses({ data: [{ thesis_urn: '', ticker: '', direction: '', state: '', conviction_score: 0, expected_horizon_days: 0 }], pagination: { total_pages: 1, total_elements: 1 } });
    expect(list.data[0].convictionScoreRaw).toBe(0);
  });
});
