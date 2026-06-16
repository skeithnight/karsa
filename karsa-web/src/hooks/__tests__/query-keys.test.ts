import { describe, it, expect } from 'vitest';
import { queryKeys } from '../query-keys';

describe('queryKeys', () => {
  it('protects portfolio query keys', () => {
    expect(queryKeys.portfolio.summary()).toEqual(['portfolio', 'summary']);
    expect(queryKeys.portfolio.exposure()).toEqual(['portfolio', 'exposure']);
  });

  it('protects theses query keys', () => {
    expect(queryKeys.theses.list({ pagination: { page: 1, size: 50 } })).toEqual(['theses', 'list', { pagination: { page: 1, size: 50 } }]);
    expect(queryKeys.theses.detail("123")).toEqual(['theses', 'detail', "123"]);
    expect(queryKeys.theses.lineage("123")).toEqual(['theses', 'lineage', "123"]);
  });

  it('protects research query keys', () => {
    expect(queryKeys.research.list({ limit: 50 })).toEqual(['research', 'list', { limit: 50 }]);
  });

  it('protects memos query keys', () => {
    expect(queryKeys.memos.list({ pagination: { page: 1, size: 50 } })).toEqual(['memos', 'list', { pagination: { page: 1, size: 50 } }]);
  });

  it('protects analysts query keys', () => {
    expect(queryKeys.analysts.metrics()).toEqual(['analysts', 'metrics']);
  });

  it('protects performance query keys', () => {
    expect(queryKeys.performance.attribution({ start_date: '2025-01-01', end_date: '2025-12-31' })).toEqual(['performance', 'attribution', { start_date: '2025-01-01', end_date: '2025-12-31' }]);
  });

  it('protects governance query keys', () => {
    expect(queryKeys.governance.list({ limit: 50 })).toEqual(['governance', 'list', { limit: 50 }]);
  });

  it('protects search query keys', () => {
    expect(queryKeys.search.results('tesla')).toEqual(['search', 'results', 'tesla']);
  });
});
