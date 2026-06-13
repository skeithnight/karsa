# ADR-001 Workspace Lineage
**Status:** Approved
**Context:** Root folders are mutable and dangerous for multi-agent concurrency.
**Decision:** Workspaces will be modeled as first-class, branchable domain entities with snapshot IDs.
**Consequences:** Enables perfect replayability but increases physical storage requirements.
