# Thesis Evolution Engine Design

## 1. Executive Summary
The Sprint-47 Thesis Evolution Engine architecture final revision formally establishes the definitive structure of the Virtual Investment Firm's strategic boundary. By adopting a strict Versioned Assumption State Model (Option A), the architecture explicitly separates canonical assumption identity from immutable, versioned assumption states. This guarantees perfect historical replayability spanning decades, fully preserving the exact contextual configurations of confidence bounds, external challenges, and calibrations natively attached to explicit chronological checkpoints. The design cleanly maps into the organizational Knowledge Graph, ensuring uncorrupted historical audits and structural fidelity across all operational horizons.

## 2. Architecture Decision
**Option Selected**: Option A (Stable Identity + Versioned Immutable State).

**Justification**: Option B (Stable Identity + Mutable Current State) fundamentally violates the foundational firm rule of historical immutability. If an assumption state mutates in place, all historical `ThesisSnapshot` records relying on that assumption retrospectively lose their point-in-time context. By explicitly decoupling `AssumptionIdentity` from `AssumptionVersion`, the architecture enables a `ThesisSnapshot` to reference a specific immutable version of an assumption (e.g., `Assumption A, v2`). This ensures that 10-year historical playbacks pull the exact logic used on the evaluation date without confronting anomalous mutated realities.

## 3. Revised Domain Model
* **`Thesis`**: Aggregate Root determining global identity (`thesis_urn`, `current_snapshot_urn`).
* **`ThesisSnapshot`**: Immutable state ledger (`snapshot_urn`, `snapshot_version`, `supersedes_snapshot_urn`, `invalidates_snapshot_urn`).
* **`ThesisAssumptionIdentity`**: Stable canonical node representing the hypothesis concept (`assumption_urn`).
* **`ThesisAssumptionVersion`**: Immutable point-in-time configuration detailing specific logic bounds and lifecycles (`assumption_urn`, `assumption_version`, `assumption_manifest_hash`, `lifecycle_state`).
* **`ThesisTransition`**: Deterministic ledger entity establishing topological pointers.
* **`ThesisDelta`**: Artifact describing exact assumption modifications across transitions.
* **`AssumptionOutcomeReference`**: First-class attribution artifact natively linked to a specific `AssumptionVersion`.
* **`ReviewReference`**: Contract payload isolating external review metadata.
* **`CalibrationReference`**: Contract payload providing algorithmically determined adjustments to base confidence.

## 4. Aggregate Design
**`Thesis`**
* **Responsibilities**: Canonical identity root, OCC lock target, and active snapshot pointer ownership.
* **Transaction Bounds**: Controls global thesis modifications; evolving a Snapshot natively requires locking the `Thesis` aggregate.

**`ThesisSnapshot`**
* **Responsibilities**: Structural preservation of evidence and bounded references to `ThesisAssumptionVersion`. Fully immutable.

**`ThesisTransition`**
* **Responsibilities**: Evolution topology tracking. Owns the `ThesisDelta`.

## 5. Assumption Identity Design
**`ThesisAssumptionIdentity`**
* **Role**: Serves exclusively as the firm-wide stable graph node.
* **Ownership Boundaries**: Exists universally decoupled from execution lifecycles, enabling continuous analytical auditing stretching across infinite snapshot variations.

## 6. Assumption Version Design
**`ThesisAssumptionVersion`**
* **Role**: Houses the explicit immutable properties bound to an execution phase.
* **Fields**: `assumption_urn`, `assumption_version`, `lifecycle_state`, `raw_confidence`, `assumption_statement`, `assumption_manifest_hash`.
* **Lineage Boundaries**: Tightly incremented linearly (`v1`, `v2`). 
* **Transaction Boundaries**: Created organically when thesis constraints change; natively committed during `ThesisSnapshot` compilation.

## 7. Knowledge Graph Model
| Subject | Direction | Target | Mutability | Cardinality | Owner | Purpose |
|---------|-----------|--------|------------|-------------|-------|---------|
| Thesis | `has_snapshot` | ThesisSnapshot | Immutable | 1:N | Thesis Engine | Temporality |
| Thesis | `has_transition`| ThesisTransition| Immutable | 1:N | Thesis Engine | Evolution Map |
| ThesisSnapshot| `references` | AssumptionVersion| Immutable | 1:N | Thesis Engine | Core Logic |
| AssumptionIdentity| `has_version` | AssumptionVersion| Immutable | 1:N | Thesis Engine | State Evolution |
| ThesisSnapshot| `supersedes` | ThesisSnapshot | Immutable | 1:1 | Thesis Engine | State Lineage |
| ThesisTransition| `supersedes` | ThesisTransition | Immutable | 1:1 | Thesis Engine | Causal Lineage |
| ThesisTransition| `owns_delta` | ThesisDelta | Immutable | 1:1 | Thesis Engine | Change Detail |
| ThesisDelta | `references` | AssumptionVersion| Immutable | N:N | Thesis Engine | Granular Shift |
| ThesisSnapshot| `originated_in`| RegimeSnapshot | Immutable | N:1 | Thesis Engine | Macro Environment |
| AssumptionVersion| `challenged_by`| ReviewReference| Immutable | 1:N | Thesis Engine | Invalidation Trigger |
| AssumptionVersion| `calibrated_by`| CalibrationReference| Immutable | 1:N | Thesis Engine | Confidence Scaling |
| OutcomeReference| `evaluates` | AssumptionVersion| Immutable | 1:1 | Thesis Engine | Execution Result |

## 8. Replayability Analysis
* **10-Year Reconstruction**: A replay engine queried decades later extracts a `ThesisSnapshot`. The snapshot explicitly points to specific `AssumptionVersion` nodes (e.g., `v2`). 
* **State Preservation**: Because `v2` is completely immutable, the replay inherently reconstructs the exact statement, the exact `raw_confidence`, and the exact historical linkages to `CalibrationReference` and `ReviewReference` without any active database policy queries.
* **Hermetic Guarantee**: The architecture permanently seals historical truths, natively averting configuration drift vulnerabilities.

## 9. ADR-085: Versioned Assumption State Model
* **Context**: Assumption identities remained stable across snapshots, but the mechanics governing internal lifecycle shifts (`ACTIVE` → `WEAKENED`) endangered historical snapshot fidelity by projecting mutable updates onto shared records.
* **Decision**: Decompose `ThesisAssumption` into `ThesisAssumptionIdentity` (canonical node) and `ThesisAssumptionVersion` (immutable state records).
* **Consequences**: Safely bounds logic. Massively enhances Knowledge Graph traversal abilities enabling exact historical state playback. Requires slightly heavier database footprint parsing pointer joins during lineage construction.
* **Rejected Alternatives**: Option B (Stable Identity + Mutable Current State) was aggressively rejected because in-place mutation fundamentally destroys retroactive analysis pathways central to the Virtual Investment Firm.

## 10. Architecture Delta Analysis
* Safely aligns with Sprints 41–46. Immutability paradigms seamlessly mirror Regime Engine structural protections, yielding zero negative friction upon global topologies.

## 11. Acceptance Criteria
* Internal architecture thoroughly establishes all immutable bounds mapping logically to real-world knowledge graphs.
* Snapshots explicitly reference strictly versioned Assumption variants.
* Playback tests execute cleanly against specific hash manifestations decoupled fully from runtime modifications.

## 12. Final Verdict
ARCHITECTURE_FROZEN
