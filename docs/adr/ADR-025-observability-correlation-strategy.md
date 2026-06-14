# ADR-025: Cross-Context Correlation Strategy

## Status
Approved

## Date
2026-06-14

## Context
Karsa’s execution flow traverses multiple decoupled bounded contexts:
- **Capability Engine**: Manages workflow states and executions.
- **Provider Abstraction**: Dynamically routes requests and executes adapters.
- **Governance Engine**: Evaluates policies and records decisions.
- **Future subsystems** (Workers, Research Runs, Theses, Portfolios, Review Sessions) will introduce additional execution scopes.

To correlate logs, metrics, and spans across these disparate boundaries without introducing direct dependencies or shared databases:
1. We must propagate business identifiers (e.g., `workflow_id`, `provider_id`, `decision_id`) along the execution call graph.
2. We must define a clear correlation hierarchy and lifecycle boundaries.
3. We must ensure that the event transport mechanism remains vendor-neutral while declaring the minimum required capabilities.

## Decision
We implement a **Cross-Context Correlation Strategy** based on the following decisions:
1. **W3C Baggage Propagation**:
   - We adopt the W3C Baggage standard for metadata propagation. Correlation variables are represented as key-value pairs propagated via execution headers (e.g. API request headers, event payload metadata, message queue properties).
2. **Standardized Correlation Context**:
   - We define a thread-safe `CorrelationContext` using Python's native `contextvars` library to store and propagate correlation keys within the execution process.
   - For asynchronous queue boundaries, the event publisher extracts the current `CorrelationContext` and serializes it into the event's headers. The consumer deserializes the headers, re-establishing the context in its thread.
3. **Correlation Hierarchy**:
   - We establish the following formal correlation hierarchy:
     ```text
     trace_id (Global root boundary)
     └── research_run_id (Group of workflow runs)
         └── thesis_id (Group of related decisions)
             └── workflow_id (Workflow execution engine coordinator)
                 ├── decision_journal_id (Narrative link)
                 ├── review_session_id (Post-mortem review link)
                 ├── worker_id (Execution node host context)
                 ├── capability_execution_id (Abstract capability span)
                 │   └── provider_execution_id (LLM provider run span)
                 ├── governance_decision_id (PDP check decision)
                 └── attribution_id (Financial cost ledger reference)
     ```
4. **Decoupled Event Streaming platform**:
   - We strip all vendor-specific message broker products (such as RabbitMQ) from the architecture in favor of a vendor-neutral **Event Streaming Platform** abstraction.
   - The streaming platform must support the following capabilities:
     * **At-Least-Once Delivery**: Messages must be successfully delivered and retried on subscriber error.
     * **Ordered Partitions**: Messages belonging to the same `trace_id` must land on the same partition to guarantee chronological event ingestion ordering.
     * **Dead Letter Queue (DLQ) Support**: Corrupted or unparseable event packets are redirected to a DLQ for operational debugging.
     * **Backpressure & Retries**: Consumer workers must implement sliding retries and flow rate control to prevent database buffer exhaustion.

## Consequences
- **Loose Coupling**: Bounded contexts remain completely independent. The Capability Engine has zero knowledge of the Governance Engine database, yet their operations are joined under the same `TraceId`.
- **Audit Traceability**: Allows audits to query the complete timeline of a decision, including the specific provider adapter run, pricing checked, policies evaluated, cost ledgers, and post-mortems.
- **Propagation Overhead**: Thread-local context switching and serialization introduce minor performance overhead. This is minimized by passing lightweight strings only.
