# ADR-051: Decision Journal Aggregate and Table Decomposition

## Status
Approved

## Context
During Sprint-37, the Decision Journal Foundation was implemented. The original frozen architecture specified a single aggregate root `DecisionJournal` mapped to a single relational database table `decision_journals`. This single table was designed to hold the initial pre-outcome reasoning log, and all subsequent corrections/revisions linked via self-referencing `parent_decision_id` and `root_decision_id` columns.

However, during implementation, this single-table approach was challenged. Combining different lifecycles (pre-outcome staging logs, revision chains, and post-outcome evidence attachments) into one entity created schema complexity, aggregate bloat, and database index degradation. Consequently, the implementation decomposed the domain model into:
* **Three aggregates**: `DecisionJournalAggregate`, `DecisionRevisionAggregate`, `DecisionEvidenceAggregate`
* **Three relational tables**: `decision_journals`, `decision_revisions`, `decision_evidences`

This ADR reviews and justifies this decomposition by challenging its impact across domain boundaries, performance, and transactional rules.

---

## Challenge Analysis

### 1. Aggregate Boundary Analysis
* *Challenge*: Does splitting one aggregate into three violate aggregate boundaries?
* *Resolution*: No. All three aggregates reside within the same `karsa.decision_journal` bounded context. They represent separate logical entries that correspond to different phases of the trade learning loop (pre-trade staging, corrections before checkout, and post-outcome trace attachments).

### 2. Transaction Boundary Analysis
* *Challenge*: Does decomposition introduce distributed transactions or cross-aggregate updates?
* *Resolution*: No. Saving a journal entry, committing a revision, or attaching post-outcome evidence are all executed as independent transactional actions. The database tables are append-only. There are no relational updates across tables.

### 3. Ownership Boundary Analysis
* *Challenge*: Does decomposition leak ownership to other contexts?
* *Resolution*: No. The Decision Journal remains the sole writer of all three tables. Downstream contexts (such as CIO Engine or Execution PEP) continue to consume these records read-only via hashes and context URNs.

### 4. Replayability Analysis
* *Challenge*: Does decomposition break deterministic replays?
* *Resolution*: No. Historical replays only require fetching the snapshot context payload from object storage. The database tables serve as reference indices mapping a unique `decision_id` to its `context_uri` and `context_hash`. Splitting references across three tables preserves mapping integrity and simplifies parent-child Directed Acyclic Graph (DAG) lineage reconstruction.

### 5. Scalability Analysis
* *Challenge*: Does decomposition scale to 10M writes/day?
* *Resolution*: Yes. Separating the logs avoids a single bloated database table. The root `decision_journals` table remains small, containing only initial trade entries. The `decision_revisions` table only grows when corrections occur, and the `decision_evidences` table handles post-trade telemetry attachments. Index sizes are reduced, keeping hot indexes in PostgreSQL RAM.

### 6. Security Analysis
* *Challenge*: Does decomposition weaken immutability?
* *Resolution*: No. Trigger functions (`block_journal_mutation`) are applied to all three tables, blocking all update and delete queries at the database layer.

---

## Alternative Designs Considered

### Option A: Retain Single self-referencing Table (Original Design)
* *Pros*: Simpler table layout (one table to manage).
* *Cons*:
  - Schema contains many nullable columns (e.g. `parent_decision_id`, `correction_reason`, `attached_evidence` details are null for root entries).
  - High B-Tree index bloat on a single table as concurrent inserts, corrections, and post-trade attachments occur simultaneously.
  - Convoluted self-referencing SQL foreign keys make daily partitioning and data archiving logic difficult.

### Option B: Multi-table / Multi-aggregate Decomposition (Implemented Design)
* *Pros*:
  - No nullable columns for revision/evidence metadata in the root `decision_journals` table.
  - Decoupled lifecycle write paths.
  - Clean indexing and daily range partitioning.
* *Cons*: Requires managing three tables and three aggregates instead of one.

---

## Reasons for Rejection of Option A
Option A was rejected because it introduces database write bottlenecks under high throughput, aggregates unrelated data lifecycles (pre-outcome planning vs post-outcome telemetry evidence) into a single database row, and complicates table partitioning.

---

## Decision
Adopt **Option B** (Multi-table and Multi-aggregate decomposition).

---

## Consequences
* **Aggregates**: Code will maintain `DecisionJournalAggregate`, `DecisionRevisionAggregate`, and `DecisionEvidenceAggregate`.
* **Database**: PostgreSQL schema will consist of `decision_journals`, `decision_revisions`, `decision_evidences`, and `active_leaf_projections` tables.
* **Events**: The event catalog is expanded to support creation, revision, and evidence attachment events.
* **Documentation**: Sprint plans, challenge-reviews, and architecture design files must be updated to align with Option B.
