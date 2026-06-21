-- Migration 002: capability_evolution_version_registry
-- Sprint-11, Wave-7. ADR-133.

CREATE TABLE IF NOT EXISTS capability_evolution_version_registry (
    version_id           TEXT PRIMARY KEY,  -- UUID
    capability_family_id TEXT NOT NULL,
    evaluation_id        TEXT NOT NULL,
    trigger_type         TEXT NOT NULL,
    evolution_id         TEXT NOT NULL,     -- URN of the evolution record
    evolution_status     TEXT NOT NULL DEFAULT 'CANONICAL',
    superseded_by        TEXT,              -- URN of the new canonical, if superseded
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- ADR-133: Exactly one CANONICAL per (family, eval, trigger)
    -- Partial unique index enforced below
    CONSTRAINT chk_evolution_status_values
        CHECK (evolution_status IN ('CANONICAL', 'SUPERSEDED', 'EXPERIMENTAL'))
);

-- ADR-133: Only one CANONICAL per (family, evaluation, trigger)
CREATE UNIQUE INDEX IF NOT EXISTS uq_version_registry_canonical
    ON capability_evolution_version_registry (capability_family_id, evaluation_id, trigger_type)
    WHERE evolution_status = 'CANONICAL';

CREATE INDEX IF NOT EXISTS idx_version_registry_family
    ON capability_evolution_version_registry (capability_family_id);

CREATE INDEX IF NOT EXISTS idx_version_registry_family_eval
    ON capability_evolution_version_registry (capability_family_id, evaluation_id);

COMMENT ON TABLE capability_evolution_version_registry IS
    'ADR-133: Canonical governance for evolution records. Exactly one CANONICAL per (family, eval, trigger).';
