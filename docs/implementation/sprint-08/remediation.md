# Sprint 08 Remediation Plan

## WP-3 Verification Findings

Before proceeding to WP-4, a verification pass was conducted on WP-3. The following gaps were discovered and must be remediated in a subsequent cycle:

1. **Postgres Metadata Repository Status**: `PostgresSnapshotRepository` is completely missing. WP-3 only implemented `InMemorySnapshotRepository` for fast integration testing. The actual relational mapping for metadata and lineage remains unbuilt.
2. **Snapshot Immutability Verification**: The `SnapshotService` does not actively prevent updates to existing records, relying only on the lack of an `update()` method in the repository. Immutability needs formal enforcement (e.g. at the DB layer via triggers or restrictive repository interfaces).
3. **Duplicate Payload Handling Strategy**: `LocalBlobStorage` currently silently overwrites files if the hash matches. This implicitly handles duplicates safely, but the strategy is not formally documented or verified.
4. **Namespace Isolation Strategy**: Implemented successfully via `os.path.join(base_path, namespace)`. However, cross-namespace hash collision handling is missing.
5. **Hash Verification on Retrieval**: `SnapshotService.get_snapshot()` reconstructs the snapshot but DOES NOT verify that the retrieved JSON payload's newly-calculated hash matches the `payload_hash` stored in the `ImmutableSnapshot` metadata. This violates zero-trust principles.

## Next Steps
These items do not require architecture redesign but do require physical code implementation. They are added to the technical debt backlog to be completed before production release.