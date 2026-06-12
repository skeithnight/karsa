# Product Requirements Document (PRD)

## Executive Summary
Karsa is an AI Software Delivery Platform that orchestrates a multi-agent workflow to transform human objectives into production-ready software. Utilizing an event-sourced architecture, state machine orchestration, and deterministic validation loops, Karsa guarantees that generated code meets rigorous quality, testing, and architectural constraints before declaring a task complete.

## Personas
1. **The Human Developer:** Defines the objectives, sets constraints, reviews final architectures, and handles complex domain integration.
2. **The Product Engineer (Agent):** The AI entity responsible for generating the code, writing tests, and fulfilling the objective constraints.
3. **The Review Agent (Agent):** The adversarial AI entity responsible for critiquing the Engineer's output, executing tests, and enforcing quality gates.

## User Problems
- Current AI assistants generate single files without tests or necessary scaffolding.
- AI workflows fail silently when API rate limits are hit or models hallucinate.
- Developers waste time copy-pasting code back and forth to fix syntax errors introduced by LLMs.
- There is no traceable history of *why* an AI made specific architectural decisions.

## Product Goals
- Achieve a 100% deterministic workflow for AI code generation.
- Eliminate the "complacency loop" where AI approves its own broken code.
- Provide full snapshot and recovery capabilities so no progress is ever lost during API outages or crashes.
- Maintain a single, immutable source of truth for every action taken by the system.

## Functional Requirements
- **Objective Ingestion:** The system must accept natural language objectives.
- **Multi-File Generation:** The system must generate complete project structures, including `README.md` and test suites.
- **Adversarial Review:** The system must feature a Review Agent that autonomously runs tests and either approves or rejects the generated artifacts.
- **Provider Abstraction:** The system must support multiple LLM providers seamlessly, falling back to alternative keys if quotas are exhausted.
- **Event Journaling:** Every state transition and artifact generation must be recorded in an append-only event journal.

## Non-Functional Requirements
- **Resiliency:** The system must recover automatically from unexpected crashes.
- **Traceability:** Every decision must be linked to a specific workflow execution and review cycle.
- **Determinism:** Workflow state machines must reject invalid transitions.
- **Security:** API credentials must be handled dynamically and isolated from runner scripts.

## Workflow Requirements
The system must follow a strict lifecycle:
1. `IDEA`: Objective is ingested.
2. `DRAFT`: The Product Engineer generates the initial implementation.
3. `REVIEW`: The Review Agent inspects the code and executes validation tools.
4. `REVISE`: The Product Engineer alters the code based on the Review Agent's feedback.
5. `APPROVED` / `FAILED`: The workflow terminates successfully or exhausts its retry limits.

## Agent Requirements
- **Strict Formatting:** Agents must output code using strict XML boundaries for parsing reliability.
- **Test Mandate:** Agents must generate executable tests (e.g., Pytest) for every artifact.
- **Execution Awareness:** Agents must interpret tool exit codes (e.g., Pytest Exit 5) correctly to govern their decisions.

## Recovery Requirements
- The system must persist snapshots of the workflow state.
- Upon failure, the system must rebuild the state machine from the Event Journal to resume exactly where it crashed.

## Acceptance Criteria
- A workflow given a valid objective must autonomously navigate from `IDEA` to `APPROVED` without human intervention.
- The final output must contain passing unit tests.
- If an API key is missing or invalid, the system must fail gracefully with a clear error message.

## Future Enhancements
- Integration with live CI/CD pipelines.
- Multi-repository dependency management.
- Dynamic Agent definition (allowing the system to spawn specialized agents as needed).
