import os

os.makedirs("docs/architecture", exist_ok=True)
os.makedirs("docs/adr", exist_ok=True)

# Phase 1: Architecture Baseline
with open("docs/architecture/ARCHITECTURE_BASELINE_V2_1.md", "w") as f:
    f.write("""# Architecture Baseline V2.1

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
""")

# Phase 2: Architecture Rewrite
with open("docs/architecture/02-multi-agent-coordination.md", "w") as f:
    f.write("""# 02 Multi-Agent Coordination

## Purpose
Decouple the rigid PE/Reviewer workflow into a dynamic DAG of specialized AI agents.

## Domain Models
```mermaid
classDiagram
    class TaskGraph {
        +String graph_id
        +List~AgentTask~ tasks
    }
    class AgentTask {
        +String task_id
        +String role
    }
```

## Interactions & Failure Scenarios
The `TaskGraph` acts as the dispatcher. If the SecurityAgent blocks an output, the TaskGraph halts dependent testing tasks and routes back to the ProductEngineer.
""")

with open("docs/architecture/03-governance-and-security.md", "w") as f:
    f.write("""# 03 Governance and Security

## Purpose
Provide capability-based AST scanning and formal FSM transition rules.

## Components
- **CapabilityRegistry**: Maps Provider limits.
- **SecurityScanner**: Validates AST against capabilities.
- **GovernanceService**: Intercepts `APPROVED` transitions and enforces `ApprovalRules`.

## Sequence Diagram
```mermaid
sequenceDiagram
    Agent->>SecurityScanner: Verify AST
    SecurityScanner-->>Agent: ALLOW
    Agent->>GovernanceService: Request FSM Transition
    GovernanceService-->>Agent: APPROVED
```
""")

with open("docs/architecture/04-workspace-and-registries.md", "w") as f:
    f.write("""# 04 Workspace and Registries

## Purpose
Ensure lineage tracking and separation of Artifacts (Code) from Evidence (Telemetry).

## Domain Models
```mermaid
classDiagram
    class Workspace {
        +String workspace_id
        +String parent_workspace_id
    }
    class ArtifactRegistry { }
    class EvidenceRegistry { }
```
""")

with open("docs/architecture/05-distributed-execution.md", "w") as f:
    f.write("""# 05 Distributed Execution

## Purpose
Execute LLM code safely via async Queues and Ephemeral Sandboxes.

## Architecture Flow
```mermaid
flowchart LR
    Planner --> Queue --> Worker --> DockerSandbox
```

## Components
- **ExecutionPlanner**: Creates ExecutionJob graphs.
- **JobQueue**: RabbitMQ/Redis future-proof abstraction.
- **DockerExecutor**: Network=none, memory=512m, non-root.
""")

with open("docs/architecture/06-observability.md", "w") as f:
    f.write("""# 06 Observability

## Purpose
Monitor cluster health, Docker latency, and OOM kills separately from the FSM journal.

## Data Flow
Worker node emits `ExecutionTelemetry` to Observability Platform (e.g., Prometheus/TSDB).
""")

# Phase 3: ADRs
for i, title in enumerate([
    "Artifact vs Evidence",
    "Capability-Based Security",
    "Execution Planner",
    "Job Queue Architecture",
    "Docker Sandbox Execution",
    "Governance Layer",
    "Multi-Agent Coordination",
    "Observability Platform"
], start=2):
    with open(f"docs/adr/ADR-{i:03d}-{title.replace(' ', '-').lower()}.md", "w") as f:
        f.write(f"""# ADR-{i:03d} {title}
**Status:** Approved
**Context:** Karsa requires scalable foundation for {title.lower()}.
**Decision:** We will implement {title}.
**Alternatives:** Use monolithic/legacy approach (Rejected).
**Consequences:** High robustness but requires careful deployment.
""")

print("Remediation Complete")
