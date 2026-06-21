-- Migration 001: capability_evolutions
-- Sprint-11, Wave-7. ADR-120, ADR-133, ADR-135, ADR-136.

CREATE TABLE IF NOT EXISTS capability_evolutions (
    -- Technical identity
    evolution_id        TEXT PRIMARY KEY,  -- URN: urn:karsa:capability:evolution:<hex>

    -- Business identity (ADR-120)
    capability_family_id TEXT NOT NULL,    -- UUID, immutable across versions
    evaluation_id        TEXT NOT NULL,    -- UUID, links to evaluation cycle
    trigger_type         TEXT NOT NULL,    -- EvolutionTriggerType enum value

    -- Capability reference
    capability_version_id TEXT NOT NULL,   -- UUID, specific version
    capability_urn        TEXT NOT NULL,   -- URN of capability at evolution time

    -- Optional upstream references
    attribution_id TEXT,                  -- URN to attribution record
    review_id      TEXT,                  -- URN to review assessment

    -- Evolution classification
    evolution_type TEXT NOT NULL,          -- EvolutionType enum value

    -- Measured change (JSONB)
    delta JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Provenance chain (JSONB)
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Child entities (JSONB arrays)
    findings        JSONB NOT NULL DEFAULT '[]'::jsonb,
    attribution_refs JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Immutable context for deterministic replay (ADR-135)
    context_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Evaluation ordering (ADR-136)
    evaluation_sequence INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- ADR-120: One evolution per trigger type per evaluation cycle
    CONSTRAINT uq_capability_evolutions_business_key
        UNIQUE (capability_family_id, evaluation_id, trigger_type),

    -- ADR-136: evaluation_sequence must be non-negative
    CONSTRAINT chk_evaluation_sequence_non_negative
        CHECK (evaluation_sequence >= 0)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_capability_evolutions_family
    ON capability_evolutions (capability_family_id);

CREATE INDEX IF NOT EXISTS idx_capability_evolutions_family_eval
    ON capability_evolutions (capability_family_id, evaluation_id);

CREATE INDEX IF NOT EXISTS idx_capability_evolutions_family_created
    ON capability_evolutions (capability_family_id, created_at);

COMMENT ON TABLE capability_evolutions IS
    'Write-once ledger of capability evolution records. ADR-120: business identity is (family, eval, trigger). ADR-133: canonical status is in version_registry, not here.';
