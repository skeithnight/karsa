-- Migration 007: capability_health_projection
-- Sprint-11, Wave-7. ADR-131, ADR-132, ADR-134, ADR-136, ADR-138.

CREATE TABLE IF NOT EXISTS capability_health_projection (
    capability_family_id       TEXT PRIMARY KEY,
    capability_urn             TEXT NOT NULL,
    current_score              FLOAT NOT NULL DEFAULT 0.5,   -- ADR-131: default 0.5
    algorithm_version          TEXT NOT NULL DEFAULT 'v1.0',  -- ADR-134

    -- 4-factor component scores (ADR-132)
    execution_quality_score    FLOAT NOT NULL DEFAULT 0.0,
    attribution_alignment_score FLOAT NOT NULL DEFAULT 0.0,
    review_sentiment_score     FLOAT NOT NULL DEFAULT 0.0,
    regime_fitness_score       FLOAT NOT NULL DEFAULT 0.0,

    evaluation_count           INTEGER NOT NULL DEFAULT 0,
    data_completeness          FLOAT NOT NULL DEFAULT 0.0,   -- ADR-131: default 0.0
    score_trend                TEXT NOT NULL DEFAULT 'UNKNOWN', -- ADR-136
    lifecycle_state            TEXT NOT NULL DEFAULT 'ACTIVE',
    last_evaluated_at          TIMESTAMPTZ,

    -- ADR-138: Governance counters
    consecutive_low_scores     INTEGER NOT NULL DEFAULT 0,
    consecutive_high_scores    INTEGER NOT NULL DEFAULT 0,

    -- Constraints
    CONSTRAINT chk_hp_current_score_range
        CHECK (current_score >= 0.0 AND current_score <= 1.0),
    CONSTRAINT chk_hp_data_completeness_range
        CHECK (data_completeness >= 0.0 AND data_completeness <= 1.0),
    CONSTRAINT chk_hp_evaluation_count_non_negative
        CHECK (evaluation_count >= 0),
    CONSTRAINT chk_hp_consecutive_low_non_negative
        CHECK (consecutive_low_scores >= 0),
    CONSTRAINT chk_hp_consecutive_high_non_negative
        CHECK (consecutive_high_scores >= 0),
    CONSTRAINT chk_hp_score_trend_values
        CHECK (score_trend IN ('IMPROVING', 'STABLE', 'DECLINING', 'UNKNOWN'))
);

COMMENT ON TABLE capability_health_projection IS
    'ADR-131: Read model for health scores. Every ACTIVE capability must have a row. Default score=0.5, completeness=0.0, trend=UNKNOWN.';
