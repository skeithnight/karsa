# ADR-020: Capability Registry Identity, Lifecycle, and Governance

## Status
Approved

## Date
2026-06-14

## Context
Karsa requires an authoritative catalog of capability specifications. To coordinate execution safely, track changes, and support reproducible workflow replays:
1. We must uniquely identify capability catalog entries.
2. We must govern capability registration and state transitions.
3. We must ensure that changes in capability definitions do not break historical executions or replays.
4. We need a way to immediately revoke or suspend compromised capabilities during security incidents.

## Decision
We implement the following architecture for the Capability Registry:
1. **Three-Tier Identity Model**: Each capability is identified using:
   - `capability_family_id`: An immutable UUIDv4 representing the capability name across all versions (useful for family-level queries).
   - `capability_id`: An immutable UUIDv4 representing a specific version of a capability definition. Used in execution traces and database logs.
   - `capability_urn`: A namespaced string with version tag (`urn:karsa:capability:{namespace}:{name}:{version}`) used for dynamic routing lookups.
2. **Contract Fingerprinting**: To detect backward compatibility violations independent of SemVer tags, Karsa computes a `contract_fingerprint` (SHA256 signature of normalized, sorted input/output JSON schemas) upon registration. Minor upgrades with breaking fingerprint signatures are rejected.
3. **Emergency Revocation Paths**: The lifecycle includes emergency states:
   - `SUSPENDED`: Temporary quarantine (suspends route resolution; can be restored).
   - `REVOKED`: Permanent quarantine. Any attempt to execute raises `RevokedCapabilityException`. Replays for this capability version fail immediately to block compromised code.
   - **Governance Ownership**: Only the Governance Engine (or security administrators) has the authority to transition a capability to `SUSPENDED` or `REVOKED`.
4. **Immutability of Active Capabilities**: Active URN versions are strictly immutable. Any schema modifications require registering a new version.

## Consequences
- **Deterministic Replayability**: Freezing capability versions prevents schema drift from breaking historical traces.
- **Trace Auditing**: The dual-key design allows renaming or refactoring a capability's URN namespace without breaking link integrity to historical database logs (which reference the immutable UUID).
- **Vulnerability Isolation**: Emergency suspension and revocation states immediately halt execution paths, protecting sandboxed workspaces.
- **High Concurrency performance**: Isolating stable metadata from fast-changing health states prevents transaction contention and aggregate lockouts.
