CREATE TABLE performance_profile_window (
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    window_value TEXT NOT NULL,
    version INT NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (target_id, target_type, window_value)
);

CREATE INDEX idx_perf_profile_target ON performance_profile_window (target_id, target_type);
