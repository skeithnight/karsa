-- Migration 006: capability_evolution_projection
-- Sprint-11, Wave-7. ADR-120, ADR-133.

CREATE TABLE IF NOT EXISTS capability_evolution_projection (
    capability_family_id   TEXT PRIMARY KEY,
    evaluation_id          TEXT NOT NULL,
    capability_urn         TEXT NOT NULL,
    total_evolutions       INTEGER NOT NULL DEFAULT 0,
    trigger_type_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    positive_evolutions    INTEGER NOT NULL DEFAULT 0,
    negative_evolutions    INTEGER NOT NULL DEFAULT 0,
    avg_score_change_bps   FLOAT NOT NULL DEFAULT 0.0,
    last_score_change_bps  FLOAT NOT NULL DEFAULT 0.0,
    last_evolution_type    TEXT NOT NULL DEFAULT '',
    last_evaluated_at      TIMESTAMPTZ,

    CONSTRAINT chk_total_evolutions_non_negative
        CHECK (total_evolutions >= 0),
    CONSTRAINT chk_positive_non_negative
        CHECK (positive_evolutions >= 0),
    CONSTRAINT chk_negative_non_negative
        CHECK (negative_evolutions >= 0)
);

COMMENT ON TABLE capability_evolution_projection IS
    'Read model: evolution summary per capability family. Rebuilt from canonical records only (ADR-133).';
