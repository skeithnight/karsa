# Sprint-28 Decision Journal Foundation - Final Remediation Review

This document contains the final architecture remediation review for Karsa's Decision Journal Foundation, evaluating the design on lineage, ownership, canonical truth selection, multi-agent compatibility, and future engine integrations.

---

## 1. Executive Summary

This review validates the architectural integrity of the Decision Journal Foundation after resolving initial challenge findings. The retired `DecisionSnapshot` aggregate root, replaced by an immutable object-store value object model, provides a secure, zero-lock baseline for pre-outcome reasoning. This final review addresses lineage models, multi-agent ownership structures, canonical truth selection, and future compatibility, confirming freeze readiness.

---

## 2. Decision Lineage Analysis

### Comparison of Lineage Options

* **Option A: Chained Lineage Tree** (`Decision A <- Correction B <- Correction C`)
  * Each correction is appended as a distinct ledger entry pointing to its immediate parent.
* **Option B: Decision Family Versioning** (`Decision Family -> Version 1, 2, 3`)
  * A flat set of versions under a parent coordinator.
* **Option C: Star Lineage Tree** (`Decision Root -> Entry A, B, C`)
  * All corrections point directly to the root decision.

### Challenge Assessment

* **Which model best supports auditability?**
  **Option A (Chained Lineage Tree)**. Chaining corrections to their immediate predecessor preserves the exact step-by-step evolutionary history and reasoning updates, making it clear *why* and *when* specific transitions occurred.
* **Which model best supports replayability?**
  **Option A**. Reconstructing the exact state of model reasoning at any point in the history requires knowing the immediate parent relationships. Chained trees allow O(1) state lookup of any intermediate node.
* **Which model best supports attribution?**
  **Option A**. Attribution scores can be mapped to the exact correction delta that altered the slippage bounds or confidence probabilities.
* **Which model best supports review and post-mortem analysis?**
  **Option A**. Post-mortems require detecting "creeping rationale updates" or attempts to retroactively align reasoning. The chained path highlights exactly which agent made which adjustment.
* **Which model minimizes ambiguity?**
  **Option A**. Chaining guarantees a Directed Acyclic Graph (DAG) representing a single historical sequence. It prevents concurrent branch collisions and sequence gap bugs.

### Final Recommendation

**Option A (Chained Lineage Tree)** is the canonical lineage model. Every correction entry must have a `parent_decision_id` pointing to the immediate parent. To support fast O(1) ancestor querying without recursive SQL traversals, the ledger table will also contain an immutable `root_decision_id` referencing the origin decision of the chain.

---

## 3. Multi-Agent Ownership Analysis

### Comparison of Multi-Agent Options

* **Option 1: One Journal Per Agent**
  * Isolated databases for each agent type. High database sprawl and complex joins.
* **Option 2: One Shared Journal**
  * Centralized registry where all agents write to the same table. Simple joins but lacks agent isolation.
* **Option 3: Decision Family with Agent Contributions**
  * Centralized, shared journal table where entries are logically grouped, with each entry explicitly tracking the contributing agent ID, signatures, and capabilities.

### Challenge Assessment

* **Which model scales best?**
  **Option 3**. A shared, range-partitioned ledger table with context payloads offloaded to object storage scales horizontally without database sprawl, while tracking agent attributes in metadata.
* **Which model preserves accountability?**
  **Option 3**. Every append contains a cryptographic signature and a `proposing_agent_id` (e.g. Research Agent, Risk Agent), ensuring verifiable ownership.
* **Which model supports attribution?**
  **Option 3**. The Attribution Engine can query the database directly to correlate success/failure to the specific agent that proposed the decision or correction.
* **Which model supports post-mortem analysis?**
  **Option 3**. Post-mortems can pinpoint which agent introduced flawed assumptions or missed limits.
* **Which model supports future autonomous agent competition?**
  **Option 3**. Multiple proposing agents can write competing decisions (branches) for the same target, allowing the CIO Agent to select the authoritative leaf.

### Final Recommendation

**Option 3 (Decision Family with Agent Contributions)** is selected. The ledger is shared but strictly partition-isolated, with every record carrying the initiating agent's cryptographic signature and identity metadata.

---

## 4. Canonical Truth Selection Analysis

At trade execution time, downstream systems must select a single authoritative pre-outcome reasoning record.

### State and Selection Model

```
       [Proposed / Recorded]
                 |
        +--------+--------+
        |                 |
   [Superseded]     [Abandoned]
        |                 |
  (Implicitly      (No matching
   referenced by    downstream
   child entry)    execution event)
        |
        v
  [Authoritative]
  (Leaf node where created_at < execution_started_at)
```

1. **How is the authoritative decision selected?**
   The authoritative decision is the **active leaf node** of the lineage chain (the leaf node where `root_decision_id = :root_id`) resolved by traversing parent links, satisfying the constraint that the record was created **before** execution began.
2. **How are superseded decisions represented?**
   A decision is implicitly superseded if a child entry exists referencing it via `parent_decision_id`. No mutable fields or updates are allowed.
3. **How are abandoned decisions represented?**
   An abandoned decision is one that has no matching execution event in the downstream logs. The Decision Journal does not update status; abandonment is resolved by the absence of a correlation link in the Performance/Attribution databases.
4. **How do downstream systems discover the active decision?**
   Downstream engines query the database:
   ```sql
   SELECT * FROM decision_journals 
   WHERE root_decision_id = :root_id 
     AND created_at < :execution_started_at
     AND decision_id NOT IN (
         SELECT parent_decision_id FROM decision_journals 
         WHERE parent_decision_id IS NOT NULL
     );
   ```
5. **How do replay processes determine the correct version?**
   The execution record links directly to the specific `decision_id` of the leaf node active at the time of execution. Replay processes load this exact record directly.

---

## 5. Aggregate Boundary Analysis

* **`DecisionJournal`** is the single **Aggregate Root**. It models an immutable, write-once ledger entry.
* **`DecisionSnapshot`** is retired to prevent aggregate inflation.
* **`DecisionContext`** is a nested **Value Object** representing the point-in-time parameters. To prevent database bloat, the bulk payload is saved to an immutable, versioned object store with Object Lock, while the relational record stores only `context_hash` (SHA-256) and `context_uri`.

---

## 6. Event Contract Analysis

Events emit only lightweight metadata and hashes to prevent data leakage and broker bottlenecks:

* `DecisionJournalCreatedEvent`
  * `event_id`, `correlation_id`, `decision_id`, `root_decision_id`, `proposing_agent_id`, `context_hash`, `context_uri`, `timestamp`
* `DecisionJournalCorrectedEvent`
  * `event_id`, `correlation_id`, `decision_id`, `parent_decision_id`, `root_decision_id`, `proposing_agent_id`, `context_hash`, `context_uri`, `timestamp`

---

## 7. Replay Determinism Analysis

- **Replay Source of Truth**: The immutable object store containing prompt templates, model weights, and environment variables.
- **Clock drift safety**: Rather than using client-side agent timestamps, the database uses transaction-generated `created_at` timestamps for validation checks, guaranteeing monotonic progress.

---

## 8. Scalability Analysis

- **SQL Write Path**: Write-once appends without updates or OCC locks mean writes are O(1) and scale linearly.
- **Payload Offloading**: Moving bulk JSON payloads to object storage reduces the SQL database write footprint to <1KB per entry.
- **Search Scale**: Decoupled asynchronously via database Change Data Capture (CDC) streaming to an OpenSearch indexing cluster.

---

## 9. Security Analysis

- **Hindsight Prevention**: Database-level constraints block all `UPDATE` and `DELETE` SQL operations.
- **Verification**: Downstream engines reject any journal inputs created after execution started.
- **Integrity**: SHA-256 cryptographic hashes ensure that downloaded context payloads match the original database metadata.

---

## 10. Architecture Delta Analysis

| stage / context | pre-sprint-28 baseline | post-sprint-28 remediated design | gaps resolved |
| :--- | :--- | :--- | :--- |
| **Decision** | No formal pre-outcome reasoning. | Strictly immutable append-only lineage tree with object-store offloading. | Eliminates hindsight bias and provides clean baseline for performance scorecard scoring. |
| **Integrations** | Downstream engines lacked validation boundaries. | Enforces `created_at < execution_started_at` verification checks. | Complete isolation against retroactive rationale injection. |

---

## 11. Required Documentation Updates

1. **docs/architecture/18-decision-journal.md**:
   * Add the `root_decision_id` column to the SQL table.
   * Add the canonical selection query for retrieving the authoritative leaf node.
   * Detail the selection and state transition model (Superseded, Abandoned, Authoritative).
2. **docs/adr/ADR-040-decision-journal-immutable-record-model.md**:
   * Document the selection of Option A (Chained Lineage Tree) and Option 3 (Shared Journal with Agent Contributions).
   * Formally detail the retirement of OCC in favor of write-once appends.

---

## 12. Findings Matrix

| Finding ID | Title | Description | Severity | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FIND-28.6** | Chained Lineage Traverse Latency | Querying parent links recursively to find the active leaf node introduces latency. | **Low** | **RESOLVED** (Introduced `root_decision_id` for flat leaf querying). |
| **FIND-28.7** | Clock Drift Vulnerability | Using agent-system clocks for pre-execution timestamps risks hindsight bypass. | **High** | **RESOLVED** (Mandated database transaction-generated timestamps). |

---

## 13. Final Verdict

**ARCHITECTURE_APPROVED**
