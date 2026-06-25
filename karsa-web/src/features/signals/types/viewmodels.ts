/**
 * Sprint-63: Signals ViewModels
 * Unified signal representation merging theses and memos.
 */

export type SignalAction = 'BUY' | 'SELL' | 'HOLD';
export type SignalStatus = 'Pending' | 'Approved' | 'Rejected';
export type SignalSource = 'thesis' | 'memo';

export interface SignalVM {
  id: string;
  ticker: string;
  action: SignalAction;
  status: SignalStatus;
  summary: string;
  conviction: string;
  target: string | null;
  stop: string | null;
  size: string | null;
  style: string | null;
  thesisId: string;
  source: SignalSource;
}
