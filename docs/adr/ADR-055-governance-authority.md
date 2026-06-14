# ADR-055: Governance Engine Authority and Ownership Boundaries

## Status
Accepted

## Context
The Sprint-41 Governance Engine Foundation requires a formal definition of its authoritative boundaries, aggregate roots, and prohibited write paths. This ADR codifies the role of the Governance Engine as the authoritative control plane of the Virtual Investment Firm (VIF), establishing it as the sole owner of compliance limits, cryptographic authorization rules, exception tokens, and the decision ledger.

## Decision
We establish the following rules for Governance context authority:

1. **Exclusive Bounded Context Ownership**:
   - The Governance Engine bounded context has exclusive write authority over all compliance limit policies, authorization public keys, and cryptographic exception overrides.
   - No other bounded context (including the CIO Engine, Risk Engine, or Execution Engine) is permitted to write directly to Governance tables.

2. **Aggregate Roots & Boundaries**:
   - `CompliancePolicy`: Owns compliance limit configurations (e.g., VaR caps, Gini index caps, leverage ceilings). Merges the proposal workflow internally (`DRAFT` $\to$ `REVIEW` $\to$ `APPROVED` $\to$ `ACTIVE` $\to$ `RETIRED`).
   - `AuthorizationPolicy`: Owns the registered public keys and roles authorized to sign exception overrides and policy proposals.
   - `ExceptionToken`: Represents cryptographically signed limits overrides mapping specific orders to elevated numeric boundaries.
   - `GovernanceDecisionRecord`: Represents the write-once ledger record of actual pre-trade checkout evaluation outcomes.

3. **Prohibited Write Paths**:
   - **Risk Engine** is prohibited from updating compliance rules or granting exception overrides.
   - **Capital Allocation Engine** is prohibited from exceeding active compliance policy bounds or modifying cash floors.
   - **CIO Engine** is prohibited from authorizing executions that breach active limits unless a valid `ExceptionToken` is registered.
   - **Execution Engine PEP** is prohibited from bypassing signature checks or modifying active policies/exceptions.
   - **Governance Engine** is prohibited from writing to execution order records, risk records, or portfolio position tables.

4. **Service-Based Interaction**:
   - All state transitions must occur via the `PolicyLifecycleService` and `ExceptionService` to ensure validation and database trigger compliance.

## Consequences
- Decouples pre-trade limit verification from transactional execution and ex-ante risk modeling.
- Enforces strict role-based separation of duties, ensuring only authorized signatures (CIO + Compliance) can alter active compliance states.
- Prevents database level tampering or unauthorized writes from other engines.
