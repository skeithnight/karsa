-- Migration 005: capability_evolution_outbox
-- Sprint-11, Wave-7. Transactional outbox for durable event publishing.

CREATE TABLE IF NOT EXISTS capability_evolution_outbox (
    outbox_id     TEXT PRIMARY KEY,           -- UUID
    event_type    TEXT NOT NULL,
    payload       TEXT NOT NULL,              -- JSON string
    aggregate_id  TEXT NOT NULL,              -- capability_family_id
    status        TEXT NOT NULL DEFAULT 'PENDING',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at       TIMESTAMPTZ,
    retry_count   INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT chk_outbox_status
        CHECK (status IN ('PENDING', 'SENT', 'FAILED'))
);

-- FOR UPDATE SKIP LOCKED support: index on (status, created_at)
CREATE INDEX IF NOT EXISTS idx_outbox_status_created
    ON capability_evolution_outbox (status, created_at)
    WHERE status = 'PENDING';

-- Dead-letter support: index on (status, retry_count)
CREATE INDEX IF NOT EXISTS idx_outbox_status_retry
    ON capability_evolution_outbox (status, retry_count)
    WHERE status = 'FAILED';

COMMENT ON TABLE capability_evolution_outbox IS
    'Transactional outbox. FOR UPDATE SKIP LOCKED for concurrent worker access.';
