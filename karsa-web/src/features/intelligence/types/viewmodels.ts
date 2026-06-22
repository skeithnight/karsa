/**
 * Intelligence Feature ViewModels
 * Phase-3: Type-safe DTOs for thesis intelligence data
 */

/** Timeline event for thesis lifecycle */
export interface TimelineEventViewModel {
  event_type: string;
  event_date: string; // ISO 8601
  description: string;
  metadata: Record<string, unknown>;
}

/** Confidence history entry */
export interface ConfidencePointViewModel {
  date: string; // ISO 8601
  confidence: number; // 0.0-1.0
  analyst: string;
}

/** Assumption intelligence */
export interface AssumptionViewModel {
  assumption_id: string;
  description: string;
  status: 'VALID' | 'INVALID' | 'UNTESTED';
  confidence: number;
  last_tested: string | null; // ISO 8601
}

/** Thesis health summary */
export interface ThesisHealthViewModel {
  thesis_urn: string;
  health_score: number; // 0.0-1.0
  valid_assumptions: number;
  total_assumptions: number;
  last_updated: string; // ISO 8601
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
}
