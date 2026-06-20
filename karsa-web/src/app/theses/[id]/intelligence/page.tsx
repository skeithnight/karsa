'use client';
import React, { use } from 'react';
import { useThesisTimeline, useConfidenceHistory, useAssumptionIntelligence, useThesisHealth } from '../../../../hooks/intelligence';
import { PageHeader } from '../../../../components/shared/PageHeader';
import { MetricCard } from '../../../../components/shared/MetricCard';
import { LoadingSkeleton } from '../../../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../../../components/shared/ErrorState';

export default function ThesisIntelligenceWorkspace({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params);
    const { id: urn } = resolvedParams;

    const { data: health, isLoading: isHealthLoading, isError: isHealthError } = useThesisHealth(urn);
    const { data: timeline, isLoading: isTimelineLoading, isError: isTimelineError } = useThesisTimeline(urn);
    const { data: confidence, isLoading: isConfidenceLoading, isError: isConfidenceError } = useConfidenceHistory(urn);
    const { data: assumptions, isLoading: isAssumptionsLoading, isError: isAssumptionsError } = useAssumptionIntelligence(urn);

    if (isHealthError || isTimelineError || isConfidenceError || isAssumptionsError) {
        return <ErrorState errorMessage="Failed to load intelligence data" />;
    }

    if (isHealthLoading || isTimelineLoading || isConfidenceLoading || isAssumptionsLoading) {
        return (
            <>
                <PageHeader title="Loading Intelligence..." description="Retrieving deep analytical logic" />
                <LoadingSkeleton variant="page" />
            </>
        );
    }

    return (
        <div className="space-y-8">
            <PageHeader title="Thesis Intelligence" description={`URN: ${urn}`} />

            <section>
                <h2 className="text-xl font-bold mb-4">Health Overview</h2>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <MetricCard title="Health Score" metric={`${health.health_score.toFixed(1)}%`} statusIndicator={health.health_status === "HEALTHY" ? "positive" : "negative"} />
                    <MetricCard title="Status" metric={health.health_status} statusIndicator={health.health_status === "HEALTHY" ? "positive" : "negative"} />
                    <MetricCard title="Valid Assumptions" metric={`${health.valid_assumptions} / ${health.total_assumptions}`} statusIndicator="neutral" />
                    <MetricCard title="Invalid Assumptions" metric={`${health.invalid_assumptions}`} statusIndicator={health.invalid_assumptions > 0 ? "negative" : "positive"} />
                </div>
            </section>

            <section>
                <h2 className="text-xl font-bold mb-4">Confidence History</h2>
                <div className="border rounded-xl p-4 bg-white dark:bg-slate-900">
                    {/* Placeholder for LineChart */}
                    {confidence.map((c: any) => (
                        <div key={c.id} className="text-sm">
                            {new Date(c.timestamp).toLocaleString()} - Confidence: {c.new_confidence} (Delta: {c.delta > 0 ? '+' : ''}{c.delta}) - {c.rationale}
                        </div>
                    ))}
                </div>
            </section>

            <section>
                <h2 className="text-xl font-bold mb-4">Timeline Lineage</h2>
                <div className="border rounded-xl p-4 bg-white dark:bg-slate-900">
                    {timeline.map((t: any) => (
                        <div key={t.event_id} className="mb-2 pb-2 border-b last:border-0 text-sm">
                            <span className="font-bold text-blue-600">{t.event_type}</span> - {new Date(t.timestamp).toLocaleString()}
                            <p className="text-slate-600 mt-1">{t.rationale || "No rationale provided"}</p>
                            <p className="text-xs text-slate-400">Actor: {t.actor_urn}</p>
                        </div>
                    ))}
                </div>
            </section>

            <section>
                <h2 className="text-xl font-bold mb-4">Assumption Intelligence</h2>
                <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 space-y-4">
                    {assumptions.map((a: any) => (
                        <div key={a.assumption_urn} className="border p-4 rounded bg-slate-50 dark:bg-slate-800">
                            <h3 className="font-bold">{a.assumption_urn}</h3>
                            <p className="mb-2">{a.statement}</p>
                            <div className="flex space-x-4 mb-2 text-sm">
                                <span className={`px-2 py-1 rounded ${a.is_valid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                    {a.is_valid ? 'VALID' : 'INVALID'}
                                </span>
                                <span className="px-2 py-1 bg-slate-200 rounded text-slate-800">
                                    Challenges: {a.challenge_count}
                                </span>
                            </div>
                            <div className="text-xs space-y-1">
                                {a.timeline.map((t: any) => (
                                    <div key={t.event_id}>
                                        <span className="font-semibold">{t.event_type}</span> - {t.rationale} ({new Date(t.timestamp).toLocaleString()})
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}
