# Architecture Baseline V2.1

## Architecture Principles
- Async-First Execution: Decouple FSM Orchestrator from Executor via Job Queues.
- Least Privilege: Limit AST capabilities dynamically per workflow.
- Immutable Lineage: Git-like workspaces for safe replays.

## Architecture Goals
Provide a robust multi-agent distributed foundation for the AI Software Company.

## Approved Components
- WorkspaceManager, ArtifactRegistry, EvidenceRegistry, ExecutionPlanner, JobQueue, QueueWorker, DockerExecutor, SecurityScanner, GovernanceService, TaskGraph.

## Deferred Components
- KubernetesExecutor, Grafana Dashboards, Remote Multi-Node Deployment (testing locally first).

## Out of Scope
- Custom Provider Integration (OpenAI/Anthropic) until Gemini execution is flawless.

## Sprint Mapping
- Epic A: Workspace Foundation
- Epic B: Security Architecture
- Epic C: Queue & Execution Engine
- Epic D: Multi-Agent Coordination
- Epic E: Governance Layer
- Epic F: Execution Observability

## Implementation Constraints
- No native `subprocess.run` testing. All tools must run in Docker Sandbox.
