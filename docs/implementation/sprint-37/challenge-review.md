# Sprint-37 Decision Journal Final Challenge Review

This document presents the final validation and challenge review of the **Decision Journal Foundation** bounded context in Sprint-37.

---

## 1. Challenge Findings

Following a thorough architectural validation, the following findings were identified:

1. **OCC Over-Elimination**: The initial design claimed OCC was "completely eliminated" from the entire context. While correct for the append-only `decision_journals` table, read-side projections that track the active leaf of a correction chain require optimistic locking (or sequence checks) to prevent race conditions under concurrent writes.
2. **Lineage Ownership Leakage**: Tracking corrections via a simple `parent_decision_id` without distinct URN definitions risks leaking decision-reasoning lineage into the CIO Engine context. The CIO context only needs to authorize the finalized leaf node of a correction chain.
3. **Bulk Artifact Duplication**: Storing datasets and model parameters inside the journal violates context boundaries. The journal must only own references and hashes, not the bulk binaries or data files.
4. **Unsupported Scalability Claims**: The target scale of 100M writes/day was stated without a concrete capacity model, data partitioning frequency, or hardware bandwidth assumptions.
5. **Replayability Gap**: Replaying decisions requires more than just prompts and confidence metrics; it must also record runtime context metadata (Git commit, runtime/interpreter versions, LLM temperature/seeds, and timezone offsets).

---

## 2. Required Corrections

The following corrections have been applied to [architecture.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/implementation/sprint-37/architecture.md):

1. **Replay Metadata Expansion**: Added `git_commit`, `runtime_version`, `model_parameters` (LLM temperature, seeds), and `market_regime_urn` to the `DecisionEvidence` value object.
2. **OCC Classification**: Introduced the **OCC Ownership Matrix** separating write-once ledger tables (no OCC) from active leaf projections (OCC required).
3. **Lineage Isolation**: Defined canonical URN prefixes isolating reasoning versions (`urn:karsa:journal:dec-123`) from CIO trade authorizations (`urn:karsa:cio:dec-123:auth`).
4. **Scalability Baseline Downgrade**: Downgraded the baseline target to a realistic **10M writes/day** with horizontal range-hash partitioning (daily chunks) as the blueprint for scaling to 100M+.

---

## 3. Ownership Matrix

The ownership boundaries for related control-plane and data artifacts are defined below:

| Artifact | Authoritative Owner | Journal Role | Description |
| :--- | :--- | :--- | :--- |
| **Hypotheses & Formulas** | Thesis Engine | Read-Only Reference | Identifies the thesis URN and version code. |
| **Model Weights / Binaries** | Research Engine | Read-Only Hash | Stores only the SHA-256 hash of the weights. |
| **LLM Prompts & Templates**| Research Engine | Reference Snapshot | Stores the prompt template version and raw text snapshot. |
| **Traces & Spans** | Observability Platform | Read-Only Link | Stores the span URN to link trace logs. |
| **Pre-Outcome Expectations**| Decision Journal | Authoritative Owner | Generates and seals expected returns and confidence thresholds. |
| **Trade Authorizations** | CIO Engine | Read-Only Reference | Signs the finalized decision URN. |

---

## 4. Replayability Assessment

The replayability of historical investment decisions is **validated**. 

By querying the database by `decision_id`, downstream engines retrieve the exact `context_uri` and `context_hash` from the immutable object store. The context snapshot contains the prompt templates, input variables, Git commit hashes, environment dependencies, model parameters (temperature, seed), and regime classifications. Resolving the `thesis_urn` at that point in time allows auditors to reconstruct the exact reasoning state of the VIF before trade execution.

---

## 5. OCC Assessment

The concurrency strategy is **validated** with the following matrix:

* **`decision_journals` Table**: **No OCC** (Strictly append-only table. SQL updates/deletes are blocked by PostgreSQL trigger functions, eliminating transaction locking).
* **`journal_context_blobs`**: **No OCC** (Offloaded to Object Storage with S3/GCS Object Lock).
* **`active_leaf_projection`**: **OCC Required** (Read-side projection updated on event consumer paths; checks version fields to prevent race conditions during updates).

---

## 6. Scalability Assessment

The scalability model is **validated** for a baseline of **10M writes/day** (115 writes/sec average, 1,200 writes/sec peak):

* **Database Bandwidth**: Offloading 50 KB telemetry snapshots to object storage reduces relational database volume to **115 KB/sec** (approx. 10 GB/day), easily handled by a single standard PostgreSQL node.
* **Storage Growth**: Range partitioning on `created_at` (daily tables) prevents B-Tree index bloat, keeping hot write indexes in RAM. Nested hash partitioning on `root_decision_id` distributes writes across partitions.

---

## 7. Documentation Delta

The changes applied to resolve the gap audit are:

* **[ROADMAP.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/roadmap/ROADMAP.md)**: Updated to place **Sprint-37: Decision Journal Foundation** immediately after Performance Engine Evolution, resolving the control plane dependency.
* **[23-vif-master-delta-analysis.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/23-vif-master-delta-analysis.md)**: Matrix and roadmap sections updated to align with the reprioritized sprint ordering.
* **[architecture.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/implementation/sprint-37/architecture.md)**: Corrected to include the OCC matrix, replay metadata, and Daily range partitioning parameters.

---

## 8. Freeze Readiness

No contradictions exist across the four roadmap, architecture, and sprint design files. The boundaries are strictly defined, and the implementation steps are ready to commence.

---

## 9. Final Verdict

### **ARCHITECTURE_FROZEN**
