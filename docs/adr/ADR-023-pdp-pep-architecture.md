# ADR-023: PDP-PEP Interception and Replay Bypass Architecture

## Status
Approved

## Date
2026-06-14

## Context
Decoupling policy configuration from the runtime engine requires a standardized interception model:
1. Every capability execution, provider routing, or resource utilization step must be checked against compliance rules.
2. In-memory replay determinism mandates that past workflows re-run without recalculating costs or re-evaluating rules.
3. Execution authorization must not propagate outage risks from the Attribution Engine.

## Decision
We implement a decoupled Policy Decision Point (PDP) and Policy Enforcement Point (PEP) architecture:

1. **Policy Decision Point (PDP)**: Evaluates constraints and returns a `GovernanceDecision`.
2. **Policy Enforcement Point (PEP)**: Intercepts actions in the host execution loops (e.g. `CapabilityPEP`).
3. **Replay Determinism (Bypass Path)**: During workflow replays, the PEP is bypassed. The engine loads the original historical `GovernanceDecision` or `ExecutionEvidence` directly, ensuring that later policy or pricing changes do not alter replay outcomes.
4. **Governance Budget Cache**: The PDP reads budget balances locally from a `GovernanceBudgetCache` pushed asynchronously by the Attribution Engine. 
   - *Outage Handling*: If the Attribution Engine is offline, the PDP evaluates against the cached snapshot.
   - *Stale Cache Policy*: Snapshots older than `max_stale_limit` (60 seconds) trigger an execution block (`StaleBudgetSnapshotError`).
5. **Emergency Override Mode**: If the Governance Engine is down, PEP fails closed by default. Administrators can trigger a bypass by attaching a cryptographically signed override token to the payload. These override events bypass the PDP and write directly to an append-only security log file for audit.

## Consequences
- **Outage Isolation**: The local budget cache protects capability execution from Attribution Engine downtime.
- **Auditable Overrides**: Administrators can execute emergency actions while maintaining forensic traceability.
- **Fail-Safe Integrity**: Prevents stale budgets from leading to unchecked overruns.
