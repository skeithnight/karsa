/**
 * Governance ViewModels
 * Sprint-63: CIO Dashboard governance panel types
 */

export type MandateCheckStatus = 'pass' | 'warn' | 'fail';
export type InfrastructureServiceStatus = 'online' | 'degraded' | 'offline';

export interface MandateCheckVM {
  /** Rule name or description */
  rule: string;
  /** Current compliance status */
  status: MandateCheckStatus;
  /** Measured value (e.g., "12%", "within limit") */
  value: string;
}

export interface InfrastructureStatusVM {
  /** Service name (e.g., "PostgreSQL", "Redis", "LLM Gateway") */
  service: string;
  /** Current operational status */
  status: InfrastructureServiceStatus;
  /** Optional note or error detail */
  note?: string;
}
