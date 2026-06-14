# Sprint-41 Governance Engine Foundation Implementation Report

This document reports on the implementation of the **Governance Engine Foundation** bounded context in Sprint-41.

---

## 1. Executive Summary
The Governance Engine is established as the authoritative control plane of the Virtual Investment Firm (VIF), owning compliance policy lifecycles, authorization keys, and write-once immutable decision ledgers. 

The implementation satisfies all architectural constraints, replacing mocked PEP/PDP interfaces with active database-backed evaluation services, multi-signature cryptographic authorization, and strict database-level immutability enforcement.

---

## 2. Codebase Organization
The package is located at `src/karsa/governance/` and contains the following modules:

* [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/governance/domain/models.py): Domain aggregates and entities:
  - `CompliancePolicy` (with transition lifecycle validation and append-only state transition architecture)
  - `AuthorizationPolicy` (mapping roles to cryptographic public keys)
  - `ExceptionToken` (double-signed target-scope limits override tokens)
  - `ExceptionRevocation` (immutable revocation ledger entry)
  - `GovernanceDecisionRecord` (permanent write-once audit log)
  - `RiskStateSnapshot` (local projection of Risk calculations)
  - Compatibility stubs: `GovernanceBudgetCache`, `GovernanceAuditChain`
* [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/governance/domain/events.py): Core event contracts:
  - `PolicyCreatedEvent` (v1)
  - `PolicyActivatedEvent` (v1)
  - `PolicyRetiredEvent` (v1)
  - `ExceptionGrantedEvent` (v1)
  - `ExceptionExpiredEvent` (v1)
  - `ExceptionRevokedEvent` (v1)
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/governance/domain/repositories.py): Outbound repository interface ports.
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/governance/infrastructure/repositories.py): Outbound repository adapter implementations (InMemory, File, and Postgres).
* [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/governance/application/services.py): Core services:
  - `PolicyRegistryService`: Enforces lifecycle transitions (`DRAFT` $\to$ `REVIEW` $\to$ `APPROVED` $\to$ `ACTIVE` $\to$ `RETIRED`) and multi-signature authorization checks.
  - `ExceptionService`: Registers double-signed overrides and issues revocations.
  - `PolicyEvaluationService` (PDP): Resolves Deny-Overrides conflict resolution against active policies, verifying exception scope bounds, anti-recursion constraints, and freshness/staleness limits on Risk projections.
* [41_governance_init.py](file:///Users/dwiki.nugraha/dwikicode/karsa/alembic/versions/41_governance_init.py): Alembic schema definitions and PostgreSQL database triggers.

---

## 3. Core Calculations & Domain Logic

### Deny-Overrides PDP Evaluation
Policy rules are evaluated using in-process mappings that ensure p99 checkout latencies remain below $5\text{ms}$:
* If any matching active policy rules evaluate to `DENY`, the initial decision outcome defaults to `DENY` (Deny-Overrides).
* In fallback mode (when no portfolio snapshot cache exists), the evaluation context defaults to the most restrictive parameters (e.g. `concentration_hhi = 1.0`, `portfolio_var_95 = 0.0`).

### Cryptographic Signatures
* Overrides (`ExceptionToken`) require double-signatures (`CIO` and `COMPLIANCE_OFFICER`) generated using Ed25519.
* Signatures are validated by serializing the canonical payload format (sorted JSON keys) and executing standard cryptography verification.

---

## 4. Database Schema and Immutability
The Postgres schema is defined entirely via migration:
* **Table List**:
  - `compliance_policies` (PK: `row_id` UUID)
  - `authorization_policies` (PK: `policy_id` VARCHAR)
  - `exception_tokens` (PK: `token_hash`, range-partitioned by `expire_time`)
  - `exception_revocations` (PK: `revocation_id` UUID)
  - `governance_decision_records` (PK: `decision_id`, range-partitioned by `evaluated_at`)
  - `policy_history` (PK: `history_id` UUID)
  - `risk_state_snapshots` (PK: `portfolio_snapshot_id` VARCHAR)
* **Immutability Enforcement**:
  - A database-level trigger function `block_mutation()` intercepts all `UPDATE` or `DELETE` requests on compliance policies, authorization policies, exception tokens, revocations, and decision records, raising an exception to preserve physical ledger integrity.

---

## 5. Event and Replay Contracts
Events use logical tracking identifiers (`event_id`, `correlation_id`, `causation_id`, `event_version`). Decision records store both `portfolio_snapshot_id` and `risk_evaluation_id` to enable deterministic, audit-trail replay reconstruction without external state inference.

---

## 6. Coverage Remediation and Test Expansion
To meet the repository quality gate (branch coverage >= 90%), the test suites were significantly expanded to cover 20 target area vectors:
* **Invalid and Malformed Signatures**: Added tests validating Ed25519 signature verification rejection on payload mismatches, key rotation, and emergency key revocations.
* **Fail-Closed Repository Error Paths**: Simulated JSON/OSError exceptions, missing concurrency versions, and filesystem directory deletion to confirm repositories safely fail-closed or propagate expected errors.
* **PDP Fallback Bounds & Context Overwrite**: Verified that when Risk snapshots or budgets are missing or stale, evaluation context defaults to restrictive fallbacks (concentration = 1.0, Var = 0.0).
* **Config Loader and TOML Parsing**: Tested malformed lines, flat lines with no assignments, and non-existent configuration fallback options.
* **Mutations on Immutable Collections**: Covered all wrapped list modification attempts (`__setitem__`, `__delitem__`, `append`, etc.) across both DRAFT and ACTIVE states.
