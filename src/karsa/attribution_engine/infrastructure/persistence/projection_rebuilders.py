"""Attribution projection rebuilders — Sprint-09.

All rebuilds use attribution_version_registry for canonical filtering.
ADR-102: Only CANONICAL attributions are used in projections.
ADR-103: JOIN with registry for projection filtering.
"""
from typing import Dict, Any, List


class WorkerAttributionProjectionRebuilder:
    """Rebuilds worker attribution projection from canonical records."""

    REBUILD_SQL = """
    INSERT INTO worker_attribution_projection (
        target_urn, total_attributions, avg_quality_score,
        total_contribution_bps, last_attributed
    )
    SELECT
        c->>'target_urn' AS target_urn,
        COUNT(*) AS total_attributions,
        AVG((c->>'quality_score')::NUMERIC) AS avg_quality_score,
        SUM((c->>'contribution_bps')::NUMERIC) AS total_contribution_bps,
        MAX(r.attributed_at) AS last_attributed
    FROM attribution_records r
    JOIN attribution_version_registry v ON v.attribution_id = r.attribution_id
    CROSS JOIN jsonb_array_elements(r.contributions) c
    WHERE v.attribution_status = 'CANONICAL'
      AND c->>'dimension' = 'ALLOCATION'
    GROUP BY c->>'target_urn'
    ON CONFLICT (target_urn) DO UPDATE SET
        total_attributions = EXCLUDED.total_attributions,
        avg_quality_score = EXCLUDED.avg_quality_score,
        total_contribution_bps = EXCLUDED.total_contribution_bps,
        last_attributed = EXCLUDED.last_attributed
    """

    def rebuild(self, conn) -> int:
        """Rebuild projection. Returns number of rows affected."""
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE worker_attribution_projection")
            cur.execute(self.REBUILD_SQL)
            return cur.rowcount


class ThesisAttributionProjectionRebuilder:
    """Rebuilds thesis attribution projection from canonical records."""

    REBUILD_SQL = """
    INSERT INTO thesis_attribution_projection (
        thesis_urn, total_attributions, avg_quality_score, last_attributed
    )
    SELECT
        c->>'target_urn' AS thesis_urn,
        COUNT(*) AS total_attributions,
        AVG((c->>'quality_score')::NUMERIC) AS avg_quality_score,
        MAX(r.attributed_at) AS last_attributed
    FROM attribution_records r
    JOIN attribution_version_registry v ON v.attribution_id = r.attribution_id
    CROSS JOIN jsonb_array_elements(r.contributions) c
    WHERE v.attribution_status = 'CANONICAL'
      AND c->>'dimension' = 'THESIS'
    GROUP BY c->>'target_urn'
    ON CONFLICT (thesis_urn) DO UPDATE SET
        total_attributions = EXCLUDED.total_attributions,
        avg_quality_score = EXCLUDED.avg_quality_score,
        last_attributed = EXCLUDED.last_attributed
    """

    def rebuild(self, conn) -> int:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE thesis_attribution_projection")
            cur.execute(self.REBUILD_SQL)
            return cur.rowcount


class RegimeAttributionProjectionRebuilder:
    """Rebuilds regime attribution projection from canonical records.

    Uses correct JSONB path: context_snapshot->'regime_snapshot'->>'regime_at_evaluation'
    """

    REBUILD_SQL = """
    INSERT INTO regime_attribution_projection (
        regime_id, total_evaluations, avg_regime_effect_bps, last_attributed
    )
    SELECT
        r.context_snapshot->'regime_snapshot'->>'regime_at_evaluation' AS regime_id,
        COUNT(*) AS total_evaluations,
        AVG((c->>'contribution_bps')::NUMERIC) AS avg_regime_effect_bps,
        MAX(r.attributed_at) AS last_attributed
    FROM attribution_records r
    JOIN attribution_version_registry v ON v.attribution_id = r.attribution_id
    CROSS JOIN jsonb_array_elements(r.contributions) c
    WHERE v.attribution_status = 'CANONICAL'
      AND c->>'dimension' = 'REGIME'
    GROUP BY r.context_snapshot->'regime_snapshot'->>'regime_at_evaluation'
    ON CONFLICT (regime_id) DO UPDATE SET
        total_evaluations = EXCLUDED.total_evaluations,
        avg_regime_effect_bps = EXCLUDED.avg_regime_effect_bps,
        last_attributed = EXCLUDED.last_attributed
    """

    def rebuild(self, conn) -> int:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE regime_attribution_projection")
            cur.execute(self.REBUILD_SQL)
            return cur.rowcount
