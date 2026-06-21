-- Migration 003: capability_health_scores
-- Sprint-11, Wave-7. ADR-132, ADR-134, ADR-136, ADR-137, ADR-138.

CREATE TABLE IF NOT EXISTS capability_health_scores (
    -- Identity
    health_score_id      TEXT PRIMARY KEY,  -- UUID
    capability_family_id TEXT NOT NULL UNIQUE,  -- One per family (ADR-132)

    -- Current composite score
    current_score FLOAT NOT NULL DEFAULT 0.5,  -- 0.0-1.0, default neutral

    -- Component breakdown (JSONB array of CapabilityScoreComponent)
    score_components JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Evaluation metadata
    evaluation_count  INTEGER NOT NULL DEFAULT 0,
    last_evaluated_at TIMESTAMPTZ,

    -- ADR-137: Version boundary tracking
    current_version_id     TEXT,           -- active capability version
    last_recorded_sequence INTEGER NOT NULL DEFAULT 0,  -- ADR-136

    -- ADR-138: Governance counters
    consecutive_low_scores  INTEGER NOT NULL DEFAULT 0,
    consecutive_high_scores INTEGER NOT NULL DEFAULT 0,

    -- ADR-134: Algorithm versioning
    algorithm_version TEXT NOT NULL DEFAULT 'v1.0',

    -- OCC version
    aggregate_version BIGINT NOT NULL DEFAULT 1,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_current_score_range
        CHECK (current_score >= 0.0 AND current_score <= 1.0),
    CONSTRAINT chk_evaluation_count_non_negative
        CHECK (evaluation_count >= 0),
    CONSTRAINT chk_consecutive_low_non_negative
        CHECK (consecutive_low_scores >= 0),
    CONSTRAINT chk_consecutive_high_non_negative
        CHECK (consecutive_high_scores >= 0),
    CONSTRAINT chk_aggregate_version_positive
        CHECK (aggregate_version >= 1)
);

CREATE INDEX IF NOT EXISTS idx_health_scores_family
    ON capability_health_scores (capability_family_id);

CREATE INDEX IF NOT EXISTS idx_health_scores_score_range
    ON capability_health_scores (current_score);

COMMENT ON TABLE capability_health_scores IS
    'ADR-132: Mutable aggregate with OCC. One per capability_family. History is in capability_score_history.';
