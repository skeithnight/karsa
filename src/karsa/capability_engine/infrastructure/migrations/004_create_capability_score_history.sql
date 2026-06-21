-- Migration 004: capability_score_history
-- Sprint-11, Wave-7. ADR-132, ADR-134, ADR-136, ADR-137.

CREATE TABLE IF NOT EXISTS capability_score_history (
    capability_family_id  TEXT NOT NULL,
    evaluation_id         TEXT NOT NULL,
    evaluation_sequence   INTEGER NOT NULL,     -- ADR-136: monotonic
    capability_version_id TEXT NOT NULL,         -- ADR-137: version boundary
    score                 FLOAT NOT NULL,        -- 0.0-1.0
    algorithm_version     TEXT NOT NULL,         -- ADR-134
    components            JSONB NOT NULL DEFAULT '[]'::jsonb,
    recorded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- ADR-136: One entry per sequence per family
    CONSTRAINT uq_score_history_family_sequence
        UNIQUE (capability_family_id, evaluation_sequence),

    -- Constraints
    CONSTRAINT chk_score_range
        CHECK (score >= 0.0 AND score <= 1.0),
    CONSTRAINT chk_sequence_non_negative
        CHECK (evaluation_sequence >= 0)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_score_history_family
    ON capability_score_history (capability_family_id);

CREATE INDEX IF NOT EXISTS idx_score_history_family_version
    ON capability_score_history (capability_family_id, capability_version_id);

CREATE INDEX IF NOT EXISTS idx_score_history_family_recorded
    ON capability_score_history (capability_family_id, recorded_at);

COMMENT ON TABLE capability_score_history IS
    'ADR-132: Append-only history. ADR-136: monotonic evaluation_sequence. ADR-137: version boundaries via capability_version_id.';
