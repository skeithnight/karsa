/**
 * CIO Dashboard Mapper Tests
 * Sprint-16: Verify DTO -> ViewModel mapping and defensive coalescing
 */

import { describe, it, expect } from 'vitest';
import {
  mapPortfolioSummary,
  mapRiskTrafficLight,
  mapTodayDecision,
  mapStockDecision,
  mapGovernanceStatus,
  mapInvestmentDecision,
  mapScoreTimeseriesEntry,
} from '../mappers';

describe('mapPortfolioSummary', () => {
  it('maps complete DTO', () => {
    const dto = {
      nav: 'IDR 10.2B',
      navChangeWtd: '+2.1%',
      navChangeYtd: '+15.3%',
      sharpeRatio: 1.8,
      maxDrawdownYtd: '8.2%',
      activeHoldings: 12,
      cashPct: '5%',
    };
    const vm = mapPortfolioSummary(dto);
    expect(vm.nav).toBe('IDR 10.2B');
    expect(vm.sharpeRatio).toBe(1.8);
    expect(vm.activeHoldings).toBe(12);
  });

  it('coalesces null values', () => {
    const vm = mapPortfolioSummary({});
    expect(vm.nav).toBe('IDR 0');
    expect(vm.sharpeRatio).toBe(0);
    expect(vm.activeHoldings).toBe(0);
  });

  it('coalesces null fields', () => {
    const vm = mapPortfolioSummary({ nav: null, sharpeRatio: null });
    expect(vm.nav).toBe('IDR 0');
    expect(vm.sharpeRatio).toBe(0);
  });
});

describe('mapRiskTrafficLight', () => {
  it('maps complete DTO', () => {
    const dto = {
      metric: 'Volatility',
      current: '18%',
      limit: '22%',
      utilizationPct: 82,
      status: 'GREEN',
    };
    const vm = mapRiskTrafficLight(dto);
    expect(vm.metric).toBe('Volatility');
    expect(vm.status).toBe('GREEN');
  });

  it('defaults to GREEN', () => {
    const vm = mapRiskTrafficLight({});
    expect(vm.status).toBe('GREEN');
    expect(vm.utilizationPct).toBe(0);
  });
});

describe('mapTodayDecision', () => {
  it('maps complete DTO', () => {
    const dto = {
      ticker: 'BBCA',
      action: 'BUY',
      conviction: 'STRONG',
      targetPrice: '9,200 IDR',
      summary: 'Dividend yield + growth',
      memoId: 'memo-001',
    };
    const vm = mapTodayDecision(dto);
    expect(vm.ticker).toBe('BBCA');
    expect(vm.action).toBe('BUY');
    expect(vm.conviction).toBe('STRONG');
  });

  it('handles null optional fields', () => {
    const vm = mapTodayDecision({ ticker: 'BBCA', action: 'BUY' });
    expect(vm.conviction).toBeNull();
    expect(vm.targetPrice).toBeNull();
    expect(vm.memoId).toBeNull();
  });
});

describe('mapStockDecision', () => {
  it('maps complete DTO', () => {
    const dto = {
      ticker: 'BBCA',
      status: 'HOLD',
      currentPrice: '8,750 IDR',
      entryPrice: '8,500 IDR',
      targetPrice: '9,200 IDR',
      convictionLevel: 'STRONG',
      convictionScore: 8.5,
      analystScores: { FUNDAMENTAL: 8, TECHNICAL: 7 },
      riskFactors: ['MSCI downgrade risk'],
    };
    const vm = mapStockDecision(dto);
    expect(vm.ticker).toBe('BBCA');
    expect(vm.analystScores.FUNDAMENTAL).toBe(8);
    expect(vm.riskFactors).toContain('MSCI downgrade risk');
  });

  it('handles missing optional fields', () => {
    const vm = mapStockDecision({ ticker: 'BBCA', status: 'PASS' });
    expect(vm.entryPrice).toBeNull();
    expect(vm.analystScores).toEqual({});
    expect(vm.riskFactors).toEqual([]);
  });
});

describe('mapGovernanceStatus', () => {
  it('maps ACTIVE status', () => {
    const dto = {
      status: 'ACTIVE',
      consecutiveLowScores: 0,
      consecutiveHighScores: 1,
      suspensionThreshold: 3,
      unsuspensionThreshold: 2,
    };
    const vm = mapGovernanceStatus(dto);
    expect(vm.status).toBe('ACTIVE');
    expect(vm.suspensionThreshold).toBe(3);
  });

  it('maps SUSPENDED status', () => {
    const vm = mapGovernanceStatus({ status: 'SUSPENDED', consecutiveLowScores: 3 });
    expect(vm.status).toBe('SUSPENDED');
    expect(vm.consecutiveLowScores).toBe(3);
  });

  it('defaults to ACTIVE', () => {
    const vm = mapGovernanceStatus({});
    expect(vm.status).toBe('ACTIVE');
  });
});

describe('mapInvestmentDecision', () => {
  it('maps complete DTO', () => {
    const dto = {
      decisionId: 'd-001',
      ticker: 'BBCA',
      decisionDate: '2026-06-21',
      state: 'APPROVED',
      analystCount: 5,
      debateCount: 2,
      hasMemo: true,
      convictionLevel: 'STRONG',
      memoDecision: 'BUY',
    };
    const vm = mapInvestmentDecision(dto);
    expect(vm.decisionId).toBe('d-001');
    expect(vm.state).toBe('APPROVED');
    expect(vm.hasMemo).toBe(true);
  });

  it('handles missing optional fields', () => {
    const vm = mapInvestmentDecision({});
    expect(vm.decisionId).toBe('');
    expect(vm.convictionLevel).toBeNull();
  });
});

describe('mapScoreTimeseriesEntry', () => {
  it('maps complete DTO', () => {
    const dto = {
      evaluationSequence: 5,
      score: 0.75,
      algorithmVersion: 'v2.0',
      recordedAt: '2026-06-15T12:00:00Z',
      capabilityVersionId: 'ver-002',
    };
    const vm = mapScoreTimeseriesEntry(dto);
    expect(vm.evaluationSequence).toBe(5);
    expect(vm.score).toBe(0.75);
    expect(vm.capabilityVersionId).toBe('ver-002');
  });

  it('handles null version id', () => {
    const vm = mapScoreTimeseriesEntry({ evaluationSequence: 1, score: 0.5 });
    expect(vm.capabilityVersionId).toBeNull();
  });
});
