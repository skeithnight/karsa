# Product Requirements Document (PRD)

## Objectives
Deliver a scalable, secure, and distributed architecture to orchestrate autonomous AI coding agents.

## Core Requirements
- **Workspace Lineage:** Workspaces must support branching, snapshot IDs, and parent lineage to enable timeline reconstruction and safe rollbacks.
- **Security & Capabilities:** The system must implement AST-based capability scanning mapped to specific Providers and Models, dropping the outdated static blacklist model.
- **Execution Isolation:** All tool executions (e.g., Pytest, Ruff) must occur within ephemeral Docker containers (`DockerExecutor`) with network isolation and memory limits.
- **Governance:** A dedicated `GovernanceService` must evaluate transition requests against explicit `ApprovalRules` before permitting FSM advancement.
- **Observability:** Telemetry metrics (latency, OOM kills, queue depth) must be logged independently of the core Event Journal.
