import os
import textwrap

os.makedirs("docs/vision", exist_ok=True)
os.makedirs("docs/product", exist_ok=True)
os.makedirs("docs/architecture", exist_ok=True)
os.makedirs("docs/adr", exist_ok=True)

with open("README.md", "w") as f:
    f.write(textwrap.dedent("""\
    # Karsa: Multi-Agent Software Delivery Platform
    
    ## Project Vision
    Karsa is an open-source, event-sourced platform designed to orchestrate the "AI Software Company." Moving beyond simple conversational copilots, Karsa provides the foundational architecture to coordinate specialized AI personas (Architects, Product Engineers, Reviewers) executing complex software delivery pipelines asynchronously.
    
    ## Architecture Overview
    Karsa is split into three primary planes:
    1. **Control Plane:** Task Graphs, Workflow FSM, and Governance Services manage the high-level intent and validation.
    2. **Data Plane:** Lineage-aware Workspaces, Artifact Registries (for source code), and Evidence Registries (for telemetry) guarantee a reproducible historical audit trail.
    3. **Execution Plane:** An asynchronous Job Queue dispatches isolated tasks to ephemerally sandboxed Worker Nodes (Docker), physically isolating execution risks from the host machine.
    
    ## Major Subsystems & Workflow Lifecycle
    - **Generate:** The `TaskGraph` assigns objectives to the Product Engineer Agent, which generates source code.
    - **Secure:** The AST-based `SecurityScanner` validates the code against the `CapabilityRegistry`.
    - **Execute:** The `ExecutionPlanner` enqueues jobs to be executed in secure, network-isolated Docker containers.
    - **Govern:** The `GovernanceService` evaluates structured output (`EvidenceRegistry`) against strict `ApprovalRules` before advancing the FSM.
    
    ## Roadmap
    Our immediate trajectory targets Kubernetes deployment for the Execution Plane, unlocking massively concurrent, distributed sandbox workers to evaluate multi-agent code branches safely.
    """))

with open("docs/vision/VISION.md", "w") as f:
    f.write(textwrap.dedent("""\
    # Vision
    
    ## The Long-Term Mission
    Karsa's mission is to bridge the gap between AI code generation and enterprise software engineering. By treating AI not as a tool, but as a simulated organization of specialized agents, Karsa enables the autonomous, end-to-end delivery of mathematically proven software.
    
    ## Strategic Direction
    - **Multi-Agent Future:** Replacing monolithic LLM prompts with a `TaskGraph` of specialized personas collaborating and challenging each other.
    - **Distributed Execution Vision:** Code execution is dangerous. Karsa envisions a future where Execution Workers scale horizontally across a Kubernetes cluster, testing thousands of code permutations concurrently.
    - **Governance & Observability Vision:** Trust in AI is built on proof. Through rigid `EvidenceRegistries` and telemetry dashboards, human operators maintain total observability over the AI Software Company's output.
    """))

with open("docs/product/PRD.md", "w") as f:
    f.write(textwrap.dedent("""\
    # Product Requirements Document (PRD)
    
    ## Objectives
    Deliver a scalable, secure, and distributed architecture to orchestrate autonomous AI coding agents.
    
    ## Core Requirements
    - **Workspace Lineage:** Workspaces must support branching, snapshot IDs, and parent lineage to enable timeline reconstruction and safe rollbacks.
    - **Security & Capabilities:** The system must implement AST-based capability scanning mapped to specific Providers and Models, dropping the outdated static blacklist model.
    - **Execution Isolation:** All tool executions (e.g., Pytest, Ruff) must occur within ephemeral Docker containers (`DockerExecutor`) with network isolation and memory limits.
    - **Governance:** A dedicated `GovernanceService` must evaluate transition requests against explicit `ApprovalRules` before permitting FSM advancement.
    - **Observability:** Telemetry metrics (latency, OOM kills, queue depth) must be logged independently of the core Event Journal.
    """))

with open("docs/architecture/01-system-overview.md", "w") as f:
    f.write(textwrap.dedent("""\
    # System Overview
    Karsa employs an asynchronous, event-sourced architecture divided into a Control Plane (FSM, Governance), Data Plane (Artifacts, Evidence, Workspaces), and Execution Plane (Queues, Workers).
    """))

with open("docs/adr/ADR-001-workspace-lineage.md", "w") as f:
    f.write(textwrap.dedent("""\
    # ADR-001 Workspace Lineage
    **Status:** Approved
    **Context:** Root folders are mutable and dangerous for multi-agent concurrency.
    **Decision:** Workspaces will be modeled as first-class, branchable domain entities with snapshot IDs.
    **Consequences:** Enables perfect replayability but increases physical storage requirements.
    """))

print("Files generated successfully.")
