// @ts-nocheck
import { describe, it, expect } from 'vitest';
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
