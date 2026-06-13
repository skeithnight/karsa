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
