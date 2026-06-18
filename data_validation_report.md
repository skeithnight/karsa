# Karsa Data Validation Report

## Database Discovery
| Metric | Value |
|---|---|
| Database Version | PostgreSQL 15.18 (Debian 15.18-1.pgdg13+1) on aarch64-unknown-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit |
| Schemas | 4 |
| Tables | 79 |

## Event Journal
| Metric | Value |
|---|---|
| Total Events | 4 |
| Distinct Streams | 1 |
| Distinct Event Types | 4 |
| Latest Sequence | 4 |

## Event Types
| Event Type | Count |
|---|---|
| AttributionAssessmentSealedEvent | 1 |
| AttributionFactGeneratedEvent | 1 |
| LineageNodeAddedEvent | 1 |
| DecisionLineageCreatedEvent | 1 |


## Stream Integrity
| Stream | Events | Max Version | Status |
|---|---|---|---|
| 0206d463-d727-489d-8e6c-cc3a839e3082 | 4 | 4 | PASS |


## OCC Validation
| Validation | Result |
|---|---|
| Unknown Streams | PASS |
| OCC Integrity | PASS |

## Event Payload Validation
All payloads valid.

## Event Outbox
| Metric | Value |
|---|---|
| Total Messages | 0 |
| Pending | 0 |
| Failed | 0 |

## Attribution Validation
| Table | Row Count |
|---|---|
| attribution_lineages | 1 |
| attribution_lineage_nodes | 1 |
| attribution_facts | 1 |
| attribution_assessments | 1 |


## Referential Integrity
| Validation | Result |
|---|---|
| Nodes -> Lineages | PASS |
| Facts -> Assessments | PASS |
| Assessments -> Lineages | PASS |

## Checkpoint Validation
| Projection | Sequence | Status |
|---|---|---|
| portfolio_read_model | 0 | RUNNING |
| portfolio_read_models | 4 | RUNNING |


## Journal vs Projection Reconciliation
| Event Type | Projection Match |
|---|---|
| DecisionLineageCreatedEvent | PASS |
| LineageNodeAddedEvent | PASS |
| AttributionAssessmentSealedEvent | PASS |
| AttributionFactGeneratedEvent | PASS |

## Replay Validation
| Table | Before | After | Match |
|---|---|---|---|
| event_journal | 4 | 4 | PASS |
| attribution_lineages | 1 | 1 | PASS |
| attribution_lineage_nodes | 1 | 1 | PASS |
| attribution_facts | 1 | 1 | PASS |
| attribution_assessments | 1 | 1 | PASS |


## CQRS Consistency
| Layer | Status |
|---|---|
| Write Model | PASS |
| Journal | PASS |
| Projection | PASS |
| Read Model | PASS |

## Poison Event Detection
| Check | Result |
|---|---|
| Poison Events | PASS |

## Data Quality Score

| Area | Status |
|---|---|
| Event Journal | PASS |
| Stream Integrity | PASS |
| OCC Integrity | PASS |
| Payload Integrity | PASS |
| Outbox | PASS |
| Attribution | PASS |
| Referential Integrity | PASS |
| Checkpoints | PASS |
| Replayability | PASS |
| CQRS Consistency | PASS |

## Data Integrity Score

100 / 100

## Runtime Errors
No runtime errors detected.

## Final Verdict

`DATA_INTEGRITY_VALIDATED`