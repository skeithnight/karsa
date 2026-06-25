/**
 * Sprint-63: Signal Mappers
 * Maps thesis and memo ViewModels into unified SignalVM[].
 */

import type { ThesisVM } from '@/features/theses/types/viewmodels';
import type { InvestmentMemoVM } from '@/features/memos/types/viewmodels';
import type { SignalVM, SignalAction, SignalStatus } from '../types/viewmodels';

function mapThesisToSignal(thesis: ThesisVM): SignalVM {
  return {
    id: thesis.urn,
    ticker: extractTicker(thesis.title),
    action: 'HOLD' as SignalAction,
    status: mapStatus(thesis.status),
    summary: thesis.title ?? '',
    conviction: mapConviction(thesis.confidence),
    target: null,
    stop: null,
    size: null,
    style: null,
    thesisId: thesis.urn,
    source: 'thesis',
  };
}

function mapMemoToSignal(memo: InvestmentMemoVM): SignalVM {
  return {
    id: memo.decisionUrn,
    ticker: extractTicker(memo.intent),
    action: mapIntentToAction(memo.intent),
    status: 'Pending' as SignalStatus,
    summary: memo.intent ?? '',
    conviction: 'MEDIUM',
    target: null,
    stop: null,
    size: null,
    style: null,
    thesisId: memo.thesisUrn ?? memo.decisionUrn,
    source: 'memo',
  };
}

function extractTicker(text: string | undefined): string {
  if (!text) return 'UNKNOWN';
  const match = text.match(/\b([A-Z]{4})\b/);
  return match ? match[1] : 'UNKNOWN';
}

function mapStatus(status?: string): SignalStatus {
  switch (status?.toLowerCase()) {
    case 'active':
    case 'approved':
      return 'Approved';
    case 'invalidated':
    case 'rejected':
      return 'Rejected';
    default:
      return 'Pending';
  }
}

function mapIntentToAction(intent: string | undefined): SignalAction {
  if (!intent) return 'HOLD';
  const lower = intent.toLowerCase();
  if (lower.includes('buy') || lower.includes('long')) return 'BUY';
  if (lower.includes('sell') || lower.includes('short')) return 'SELL';
  return 'HOLD';
}

function mapConviction(confidence: number | undefined): string {
  if (!confidence) return 'LOW';
  if (confidence >= 4) return 'STRONG';
  if (confidence >= 3) return 'MEDIUM';
  return 'LOW';
}

export function mapSignals(
  theses: ThesisVM[] | undefined,
  memos: InvestmentMemoVM[] | undefined,
): SignalVM[] {
  const thesisSignals = (theses ?? []).map(mapThesisToSignal);
  const memoSignals = (memos ?? []).map(mapMemoToSignal);

  const signalMap = new Map<string, SignalVM>();
  for (const signal of thesisSignals) {
    signalMap.set(signal.id, signal);
  }
  for (const signal of memoSignals) {
    signalMap.set(signal.id, signal);
  }

  return Array.from(signalMap.values());
}
