-- Migration 008: capability_score_timeseries_projection
-- Sprint-11, Wave-7. ADR-134, ADR-136, ADR-137.

CREATE TABLE IF NOT EXISTS capability_score_timeseries_projection (
    capability_family_id  TEXT NOT NULL,
    capability_version_id TEXT NOT NULL,         -- ADR-137
    evaluation_id         TEXT NOT NULL,
    evaluation_sequence   INTEGER NOT NULL,      -- ADR-136: monotonic
    score                 FLOAT NOT NULL,        -- 0.0-1.0
    algorithm_version     TEXT NOT NULL,         -- ADR-134
    recorded_at           TIMESTAMPTZ NOT NULL,

    -- Composite primary key for uniqueness
    CONSTRAINT pk_timeseries PRIMARY KEY (capability_family_id, evaluation_sequence),

    -- Constraints
    CONSTRAINT chk_ts_score_range
        CHECK (score >= 0.0 AND score <= 1.0),
    CONSTRAINT chk_ts_sequence_non_negative
        CHECK (evaluation_sequence >= 0)
);

-- ADR-137: Version boundary queries
CREATE INDEX IF NOT EXISTS idx_timeseries_family_version
    ON capability_score_timeseries_projection (capability_family_id, capability_version_id);

CREATE INDEX IF NOT EXISTS idx_timeseries_family_recorded
    ON capability_score_timeseries_projection (capability_family_id, recorded_at);

COMMENT ON TABLE capability_score_timeseries_projection IS
    'ADR-137: Score time series. Version boundaries preserved via capability_version_id. Ordered by evaluation_sequence (ADR-136).';
