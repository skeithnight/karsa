import { useQuery } from '@tanstack/react-query';
import type {
  TimelineEventViewModel,
  ConfidencePointViewModel,
  AssumptionViewModel,
  ThesisHealthViewModel,
} from '../../features/intelligence/types/viewmodels';

/** Safely coalesce null/undefined to fallback */
function coalesce<T>(value: T | null | undefined, fallback: T): T {
  return value ?? fallback;
}

function mapTimelineEvent(dto: Record<string, unknown>): TimelineEventViewModel {
  return {
    event_type: coalesce(dto.event_type as string, ''),
    event_date: coalesce(dto.event_date as string, ''),
    description: coalesce(dto.description as string, ''),
    metadata: coalesce(dto.metadata as Record<string, unknown>, {}),
  };
}

function mapConfidencePoint(dto: Record<string, unknown>): ConfidencePointViewModel {
  return {
    date: coalesce(dto.date as string, ''),
    confidence: coalesce(dto.confidence as number, 0),
    analyst: coalesce(dto.analyst as string, ''),
  };
}

function mapAssumption(dto: Record<string, unknown>): AssumptionViewModel {
  return {
    assumption_id: coalesce(dto.assumption_id as string, ''),
    description: coalesce(dto.description as string, ''),
    status: coalesce(dto.status as 'VALID' | 'INVALID' | 'UNTESTED', 'UNTESTED'),
    confidence: coalesce(dto.confidence as number, 0),
    last_tested: (dto.last_tested as string) ?? null,
  };
}

function mapThesisHealth(dto: Record<string, unknown>): ThesisHealthViewModel {
  return {
    thesis_urn: coalesce(dto.thesis_urn as string, ''),
    health_score: coalesce(dto.health_score as number, 0),
    valid_assumptions: coalesce(dto.valid_assumptions as number, 0),
    total_assumptions: coalesce(dto.total_assumptions as number, 0),
    last_updated: coalesce(dto.last_updated as string, ''),
    status: coalesce(dto.status as 'HEALTHY' | 'DEGRADED' | 'CRITICAL', 'CRITICAL'),
  };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export function useThesisTimeline(urn: string) {
    return useQuery<TimelineEventViewModel[]>({
        queryKey: ['intelligence', 'theses', urn, 'timeline'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/api/intelligence/theses/${urn}/timeline`);
            if (!res.ok) throw new Error('Failed to fetch thesis timeline');
            const data = await res.json();
            return Array.isArray(data) ? data.map(mapTimelineEvent) : [];
        },
        enabled: !!urn,
        staleTime: 60_000,
    });
}

export function useConfidenceHistory(urn: string) {
    return useQuery<ConfidencePointViewModel[]>({
        queryKey: ['intelligence', 'theses', urn, 'confidence'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/api/intelligence/theses/${urn}/confidence`);
            if (!res.ok) throw new Error('Failed to fetch confidence history');
            const data = await res.json();
            return Array.isArray(data) ? data.map(mapConfidencePoint) : [];
        },
        enabled: !!urn,
        staleTime: 60_000,
    });
}

export function useAssumptionIntelligence(urn: string) {
    return useQuery<AssumptionViewModel[]>({
        queryKey: ['intelligence', 'theses', urn, 'assumptions'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/api/intelligence/theses/${urn}/assumptions`);
            if (!res.ok) throw new Error('Failed to fetch assumptions');
            const data = await res.json();
            return Array.isArray(data) ? data.map(mapAssumption) : [];
        },
        enabled: !!urn,
        staleTime: 60_000,
    });
}

export function useThesisHealth(urn: string) {
    return useQuery<ThesisHealthViewModel>({
        queryKey: ['intelligence', 'theses', urn, 'health'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/api/intelligence/theses/${urn}/health`);
            if (!res.ok) throw new Error('Failed to fetch thesis health');
            return mapThesisHealth(await res.json());
        },
        enabled: !!urn,
        staleTime: 60_000,
    });
}
