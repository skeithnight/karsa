
CREATE TABLE attribution_lineage (
    outcome_id VARCHAR NOT NULL,
    sequence_id INT NOT NULL,
    active_attribution_id VARCHAR NOT NULL,
    current_generation INT NOT NULL,
    version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (outcome_id, sequence_id)
);

CREATE TABLE attribution_lineage_restatement (
    outcome_id VARCHAR NOT NULL,
    sequence_id INT NOT NULL,
    approval_reference VARCHAR NOT NULL,
    generation INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (outcome_id, sequence_id, approval_reference)
);

CREATE TABLE attribution_input_projection (
    source_context_id VARCHAR PRIMARY KEY,
    contributors JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
