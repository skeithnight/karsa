import os

test_dir = "src/features/analysts/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
import { mapListAnalysts, mapAnalystMetric } from '../mappers';

describe('Analysts Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapListAnalysts({ data: [{ analyst_id: '1', role: 'worker', trust_score: 1, win_rate: 0.8, drawdown: 0.1 }] });
    expect(res.data.length).toBe(1);
    expect(res.data[0].analystId).toBe('1');
    expect(res.data[0].performanceStatus.label).toBe('Outperform');
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
    expect(res.data[0].performanceStatus.label).toBe('Underperform');
  });
});
""")

test_dir = "src/features/governance/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
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
""")

test_dir = "src/features/memos/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
import { mapListInvestmentMemos } from '../mappers';

describe('Memos Mappers', () => {
  it('handles valid DTO', () => {
    const res = mapListInvestmentMemos({ data: [{ decision_urn: '1', thesis_urn: '2', intent: 'long', pep_signature: 'sig', timestamp: '2025-01-01' }], pagination: { page: 1, size: 50, total_pages: 1, total_elements: 1 } });
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
    const res = mapListInvestmentMemos({ data: [], pagination: { page: 1, size: 50, total_pages: 0, total_elements: 0 } });
    expect(res.data).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const res = mapListInvestmentMemos({ data: [{ decision_urn: '1', thesis_urn: '2', intent: '', pep_signature: '', timestamp: '' }], pagination: { page: 1, size: 50, total_pages: 1, total_elements: 1 } });
    expect(res.data[0].intent).toBe('');
  });
});
""")

test_dir = "src/features/performance/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
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
""")

test_dir = "src/features/portfolio/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
import { mapPortfolioSummary, mapPortfolioExposure } from '../mappers';

describe('Portfolio Mappers', () => {
  it('handles valid DTO', () => {
    const sum = mapPortfolioSummary({ total_aum: 1000, daily_pnl: 100, active_theses_count: 5, net_exposure: 0.8, last_updated: '2025-01-01' });
    expect(sum.totalAumRaw).toBe(1000);
    const exp = mapPortfolioExposure({ sectors: [{ sector: 'Tech', allocation_pct: 0.5 }] });
    expect(exp.sectors.length).toBe(1);
  });
  it('handles missing array fields gracefully', () => {
    const exp = mapPortfolioExposure({} as any);
    expect(exp.sectors).toEqual([]);
  });
  it('handles null array fields gracefully', () => {
    const exp = mapPortfolioExposure({ sectors: null } as any);
    expect(exp.sectors).toEqual([]);
  });
  it('handles empty collections', () => {
    const exp = mapPortfolioExposure({ sectors: [] });
    expect(exp.sectors).toEqual([]);
  });
  it('handles edge primitive values', () => {
    const sum = mapPortfolioSummary({ total_aum: 0, daily_pnl: -100, active_theses_count: 0, net_exposure: 0, last_updated: '' });
    expect(sum.totalAumRaw).toBe(0);
  });
});
""")

test_dir = "src/features/research/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
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
""")

test_dir = "src/features/theses/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
import { mapListTheses, mapThesisDetail, mapThesisLineage } from '../mappers';

describe('Theses Mappers', () => {
  it('handles valid DTO', () => {
    const list = mapListTheses({ data: [{ thesis_urn: '1', ticker: 'AAPL', direction: 'LONG', state: 'ACTIVE', conviction_score: 5, expected_horizon_days: 30 }], pagination: { page: 1, size: 50, total_pages: 1, total_elements: 1 } });
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
    const list = mapListTheses({ data: [{ thesis_urn: '', ticker: '', direction: '', state: '', conviction_score: 0, expected_horizon_days: 0 }], pagination: { page: 1, size: 50, total_pages: 1, total_elements: 1 } });
    expect(list.data[0].convictionScoreRaw).toBe(0);
  });
});
""")

test_dir = "src/features/search/utils/__tests__"
os.makedirs(test_dir, exist_ok=True)
with open(f"{test_dir}/mappers.test.ts", "w") as f:
    f.write("""import { describe, it, expect } from 'vitest';
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
""")

