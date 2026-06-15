# Sprint-46 Regime Engine Foundation Architectural Design

This document details the architectural design for the **Regime Engine Foundation** in Sprint-46. It establishes the Regime Engine as a first-class, read-only provider of market regime intelligence within the Virtual Investment Firm architecture, respecting all closed sprint boundaries.

---

## 1. Executive Summary
The Regime Engine Bounded Context is responsible for analyzing historical and real-time market data to classify market regimes (covering market direction, volatility scaling, and liquidity states). It outputs read-only, versioned snapshots that downstream engines consume. All classifications are deterministic, replayable, and protected by database-level triggers to guarantee absolute ledger immutability.

* **Verdict**: `ARCHITECTURE_APPROVED`
* **Status**: Design Phase complete; ready to transition to Implementation Planning.

---

## 2. Ownership Boundary Matrix
The Regime Engine acts strictly as a producer of read-only market regime intelligence. It does not leak into, influence, or manage responsibilities owned by other contexts.

| Capability / Action | Owner Context | Regime Engine Role |
| :--- | :--- | :--- |
| **Classify Market Regimes** | **Regime Engine** | **Owner** (Analyzes data and writes snapshots) |
| **Track Regime Transitions** | **Regime Engine** | **Owner** (Writes explicit transition aggregates) |
| **Manage Regime History** | **Regime Engine** | **Owner** (Derived projection over Snapshot + Transition) |
| **Assign Capital Weights** | Capital Allocation | Consumer Only (Consumes regime snapshots as inputs) |
| **Rank Workers** | Capital Allocation | Consumer Only (No ranking operations performed) |
| **Worker Performance Evaluation** | Performance Engine | Consumer Only (Consumes difficulty factors) |
| **Qualitative Reviews** | Review & Post-Mortem | Consumer Only (Consumes context snapshots) |
| **Thesis Life Cycle Management** | Thesis Engine | Consumer Only (No thesis changes allowed) |
| **Manage Compliance Rules** | Governance Engine | Consumer Only (No governance writes allowed) |

---

## 3. Architecture Overview
The Regime Engine defines a strategy-based classification model. A session (`RegimeSession`) orchestrates the run. It loads the active classification strategy and applies it to segment-specific market data across specific horizons (`RegimeHorizon`). Calculated outputs are persisted as immutable `RegimeSnapshot` entries. If a snapshot represents a confirmed state change passing hysteresis checks, a `RegimeTransition` aggregate is explicitly created.

---

## 4. Domain Model
* **`RegimeSession`**: Aggregate Root managing the classification execution lifecycle.
* **`RegimeSnapshot`**: Aggregate Root representing an immutable classification ledger entry.
* **`RegimeTransition`**: Aggregate Root explicitly recording a regime state change (e.g., Bull → Bear).
* **`MarketSegment`**: Value Object representing the asset class or market index partition.
* **`RegimeHorizon`**: Value Object defining the time horizon of the classification (e.g., 30D, 90D).
* **`RegimeClassification`**: Value Object aggregating direction, volatility, and liquidity states.
* **`RegimeEvidence`**: Immutable Value Object preserving the exact signals and metrics.
* **`RegimeMethodologyManifest`**: Value Object locking the code version, policy hash, and parameters.
* **`SignalConfidenceScore`**: Value Object encapsulating the strength of the evidence signal.

---

## 5. Aggregate Design

### 5.1 RegimeTransition Lineage Ledger
`RegimeTransition` is a first-class immutable aggregate root. To support deterministic lineage reconstruction independent of timestamps or transaction orders, it implements explicit lineage pointers:
* `supersedes_transition_urn`
* `invalidates_transition_urn`
This forms an unbreakable deterministic chain that mirrors the protections established in Attribution, Performance, Review, and Capital Allocation.

### 5.2 Unique Natural Key Ownership
To ensure observation uniqueness and consistency, the architecture enforces the following natural key constraint for `RegimeSnapshot`:
`Unique Constraint: (segment_urn, horizon_urn, snapshot_date)`
* **Rationale**: This strictly guarantees exactly one active snapshot per segment/horizon/day, preventing duplicate states, ensuring determinism for downstream read consistency, and providing a singular historical anchor for replay validation.

---

## 6. Value Objects

### 6.1 `SignalConfidenceScore`
Replaces the raw Decimal confidence score to guarantee semantic safety.
```python
@dataclass(frozen=True)
class SignalConfidenceScore:
    value: Decimal # 0.00 to 1.00
    
    def validate(self):
        # Invariants ensuring 0.00 <= value <= 1.00
        pass
```
* **Semantics**: Explicitly defined as **Weighted Signal Confidence**. It represents the alignment strength of underlying signals.
* **Prohibitions**: It MUST NOT be interpreted as statistical probability, expected return, win rate, or forecast accuracy.
* **Downstream Contract**: Performance Engine, Review Engine, Capital Allocation Engine, and Thesis Engine must use this explicitly to scale internal parameters based on structural signal strength, not outcome probability.

### 6.2 `RegimeEvidence`
Preserves the exact evidence used to classify the regime and ensures complete replayability against evidence methodology drift.
```python
@dataclass(frozen=True)
class RegimeEvidence:
    evidence_type: str       
    evidence_value: Decimal
    evidence_weight: Decimal
    evidence_contribution: Decimal
    evidence_methodology_urn: str    # NEW: identifies evidence methodology
    evidence_policy_hash: str        # NEW: hash of evidence rules
    evidence_manifest_hash: str      # NEW: aggregate hash of inputs + policy
```
* **Decision**: `evidence_manifest_hash` MUST participate directly in the generation of the parent `regime_manifest_hash`. This guarantees that if evidence algorithms drift, the parent regime manifest explicitly reflects the drift, protecting historic classifications.

### 6.3 `RegimeMethodologyManifest`
Guarantees deterministic replayability against methodology drift.
```python
@dataclass(frozen=True)
class RegimeMethodologyManifest:
    regime_methodology_urn: str      
    regime_policy_hash: str          
    regime_strategy_version: str     
    parameter_hash: str              
    regime_manifest_hash: str        # Aggregate hash of all above + evidence_manifest_hash(es)
```

---

## 7. Oscillation Controls
**Option C (Hybrid hysteresis + confirmation window)** is selected to prevent daily regime thrashing (e.g., Bull ↔ Bear) while preserving determinism and auditability.
* **Hysteresis Ownership**: `RegimeTransitionService` owns the confirmation logic. It applies a mathematical hysteresis threshold.
* **Confirmation Window**: A transition is pending until the new state has been observed consecutively for $N$ days (the confirmation window).
* **Manifest Participation**: Hysteresis rules and confirmation windows are fully incorporated into the transition manifest, ensuring identical replays. Only formally confirmed transitions emit `RegimeTransition`. Raw state observations remain continuously tracked via daily `RegimeSnapshots`.

---

## 8. Application Services

### 8.1 `RegimeClassificationService`
* Orchestrates data collection, generates `RegimeEvidence`, calculates `SignalConfidenceScore`, constructs the `RegimeMethodologyManifest`, and saves the `RegimeSnapshot`.

### 8.2 `RegimeTransitionService`
* Monitors for new `RegimeSnapshots`, evaluates hysteresis rules and confirmation windows, and emits `RegimeTransition` explicitly linked via lineage pointers when confirmed.

### 8.3 `RegimeReplayService`
* Runs verification of historic classifications and transitions purely from manifest payloads.

---

## 9. Replayability Closure Model
Historical replay must depend exclusively on:
1. Snapshot Manifest
2. Evidence Manifest
3. Methodology Metadata
4. Policy Hashes

**Explicitly Prohibited Actions during Replay**:
* Active database lookups
* Runtime policy retrieval
* Mutable threshold loading
By completely severing replay operations from current execution context dependencies, historic replays are fully deterministic, cycle-safe, and infinitely repeatable.

---

## 10. Updated ADR Decisions

### ADR-067: Regime Transition Ledger
* **Decision**: `RegimeTransition` is a first-class immutable aggregate root utilizing explicit pointers (`supersedes_transition_urn`, `invalidates_transition_urn`).

### ADR-068: Regime Evidence Preservation
* **Decision**: `RegimeEvidence` tracks `evidence_methodology_urn`, `evidence_policy_hash`, and `evidence_manifest_hash` to ensure deep determinism.

### ADR-069: Regime Confidence Semantics (Weighted Signal Confidence)
* **Decision**: Implement `SignalConfidenceScore` to explicitly forbid misinterpretation as probability or expected return.

### ADR-070: Horizon Isolation for Regimes
* **Decision**: Implement `RegimeHorizon` to explicitly scope classifications (e.g., 30D vs 90D).

### ADR-071: Regime Hysteresis Controls
* **Decision**: Implement Option C (Hybrid hysteresis + confirmation window) in `RegimeTransitionService` to prevent high-frequency regime thrashing.

---

## 11. Final Verdict
```
ARCHITECTURE_APPROVED
```
