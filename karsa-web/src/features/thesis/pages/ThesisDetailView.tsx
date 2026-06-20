import React from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { MetricCard } from '../../../components/shared/MetricCard';
import { ThesisDetailVM } from '../../theses/types/viewmodels';

interface ThesisDetailViewProps {
  detail: ThesisDetailVM;
}

export function ThesisDetailView({ detail }: ThesisDetailViewProps) {
  return (
    <>
      <PageHeader title={detail.title || 'Thesis Detail'} description={detail.urn || ''} />
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
        <MetricCard title="Title" metric={detail.title || '-'} statusIndicator="neutral" />
        <MetricCard title="Author" metric={detail.author_urn || '-'} statusIndicator="neutral" />
        <MetricCard title="Regime" metric={detail.regime_urn || '-'} statusIndicator="neutral" />
        <MetricCard title="Version" metric={detail.version?.toString() || '-'} statusIndicator="neutral" />
        <MetricCard title="Confidence" metric={detail.confidence?.toString() || '-'} statusIndicator="neutral" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Lifecycle Panel</h3>
          <p className="text-sm text-slate-600 font-bold">{detail.status || 'UNKNOWN'}</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Rationale Panel</h3>
          <h4 className="text-sm font-bold mt-2">Summary</h4>
          <p className="text-sm text-slate-600 mb-2">{detail.summary || '-'}</p>
          <h4 className="text-sm font-bold">Rationale</h4>
          <p className="text-sm text-slate-600">{detail.rationale || '-'}</p>
        </div>
        <div className="col-span-1 border rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 className="font-semibold mb-2">Assumptions Panel</h3>
          <ul className="list-disc pl-4 text-sm text-slate-600 space-y-2">
            {(detail.assumptions ?? []).map((a, i) => (
              <li key={i}>
                <strong>{a.urn}</strong>
                <p>{a.statement}</p>
                <span className="inline-block px-2 py-1 bg-slate-100 rounded text-xs mt-1">
                  Validity: {a.is_valid !== false ? 'VALID' : 'INVALID'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
