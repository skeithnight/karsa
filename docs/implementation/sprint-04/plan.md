# Sprint 4 Plan

## TD-006: Multi-File Artifact Parsing Blueprint
**Goal:** Enable Karsa to generate, persist, recover, review, and resume multi-file projects while preserving existing event sourcing, checkpointing, recovery, and artifact ownership rules.
**Constraints:** Do not modify WorkflowEngine, WorkflowRunner, RecoveryEngine, EventJournal, SnapshotStrategy.
**Strategy:** 
- AgentOrchestrator parses multiple files using a deterministic `<file path="...">` format.
- Each file is persisted in ArtifactRegistry.
- A single Tree Manifest (JSON) tracks generated files and is stored in ArtifactRegistry.
- The `ExecutionCheckpointEvent` references the manifest hash.