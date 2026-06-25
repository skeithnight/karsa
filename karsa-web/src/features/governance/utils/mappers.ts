/**
 * Governance Mappers
 * Sprint-63: DTO -> ViewModel transformations for governance panel
 */

import type { RiskMetricDTO, ConglomerateExposureDTO } from '@/api/endpoints/cio-dashboard';
import type {
  MandateCheckVM,
  InfrastructureStatusVM,
} from '../types/viewmodels';

function mapStatus(raw: string): 'pass' | 'warn' | 'fail' {
  switch (raw?.toUpperCase()) {
    case 'GREEN': return 'pass';
    case 'AMBER': return 'warn';
    case 'RED': return 'fail';
    default: return 'pass';
  }
}

export function mapMandateChecks(metrics: RiskMetricDTO[] | null | undefined): MandateCheckVM[] {
  if (!metrics || !Array.isArray(metrics)) return [];
  return metrics.map((m) => ({
    rule: m.metric ?? '',
    status: mapStatus(m.status ?? 'GREEN'),
    value: m.current ?? '',
  }));
}

export function mapInfrastructureStatus(health: Record<string, unknown> | null | undefined): InfrastructureStatusVM[] {
  if (!health) return [];

  const deps = (health.dependencies ?? {}) as Record<string, unknown>;
  const dbStatus = deps.database as string | undefined;
  const storeStatus = deps.object_store as string | undefined;

  function mapStatus(val: string | undefined): InfrastructureServiceStatus {
    if (val === 'ok' || val === 'healthy' || val === 'up') return 'online';
    if (val === 'degraded' || val === 'slow' || val === 'warning') return 'degraded';
    return 'offline';
  }

  const services: InfrastructureStatusVM[] = [];

  services.push({
    service: 'PostgreSQL',
    status: mapStatus(dbStatus),
  });

  services.push({
    service: 'Object Store',
    status: mapStatus(storeStatus),
  });

  return services;
}

export function mapConglomerateLimits(dtos: ConglomerateExposureDTO[] | null | undefined) {
  if (!dtos || !Array.isArray(dtos)) return [];
  return dtos.map((d) => ({
    name: d.group ?? 'Unknown',
    exposurePct: d.exposure_pct ?? 0,
    limitPct: d.limit_pct ?? 0,
    status: d.status ?? 'OK',
  }));
}
