# Karsa

Karsa is a deterministic, AI-orchestrated software delivery platform that transforms human objectives into verified, production-ready code via a strict, multi-agent event-sourced workflow.

```text
+--------------+        +-----------------+        +-----------------+
| Human Intent | -----> | Workflow Engine | -----> | Verified Artifact|
+--------------+        +-----------------+        +-----------------+
                              |   ^
                              v   |
                        +-----------------+
                        |  AI Agents      |
                        | (Draft, Review) |
                        +-----------------+
```

## What is Karsa?
Karsa is an open-source AI Software Delivery Platform. It deviates from traditional AI coding assistants by treating software generation as a rigorous state machine rather than an interactive chat. It employs:
- **Multi-Agent Workflow:** A separation of concerns between generating code (Product Engineer) and evaluating code (Review Agent).
- **Event-Sourced Architecture:** Every LLM request, state transition, and file modification is permanently journaled.
- **Human-in-the-Loop Delivery:** Humans govern the ultimate acceptance of the software, stepping in only for strategic approvals or domain-specific integrations.

## Why Karsa?
Current AI assistants excel at generating single files but fail catastrophically when tasked with scaffolding complete architectures. They lack memory, self-correction constraints, and the ability to resume after a failure.
Karsa solves this by guaranteeing that code is never considered "done" unless it is accompanied by tests, successfully passes strict review heuristics, and respects the workflow lifecycle. If Karsa hits a rate limit or API failure, it will automatically recover from its last known snapshot without losing progress.

## Core Capabilities
| Capability | Status |
|------------|---------|
| Event-Sourced Workflows | ✅ Implemented |
| FSM State Orchestration | ✅ Implemented |
| Crash Recovery & Snapshots | ✅ Implemented |
| Multi-Agent Review Cycles | ✅ Implemented |
| Provider Key Rotation | ✅ Implemented |
| Native Test Execution Validation | ✅ Implemented |
| Multi-Provider Abstraction | ⏳ Planned |
| Dynamic Container Execution | ⏳ Planned |

## Architecture Overview
Karsa is composed of several strictly decoupled sub-systems:
1. **Agent Orchestrator:** Manages the LLM context, prompt construction, and result parsing.
2. **Workflow Engine:** A Finite State Machine that governs the sequence of development (Idea -> Draft -> Review -> Revise -> Approved).
3. **Recovery Engine:** Rebuilds the workflow from immutable events upon crash.
4. **Provider Layer:** A dynamic key-rotation pool that handles rate limiting, quotas, and multiple Google Gemini keys seamlessly.

## Workflow Lifecycle
The system follows a strict state progression:
- **IDEA:** The human objective is ingested.
- **DRAFT:** The Product Engineer agent implements the initial codebase.
- **REVIEW:** The Review Agent executes tools (e.g., Pytest) and evaluates the output.
- **REVISE:** The Product Engineer fixes any failing tests or architectural flaws.
- **APPROVED / FAILED:** The workflow either successfully validates or exhausts its retry constraints.
Because every step is backed by an `EventJournalRepository` and `SnapshotRepository`, the system can be violently interrupted at any point and gracefully resume execution.

## Current Progress
Karsa has successfully progressed through multiple implementation sprints:
- **Sprint 1 & 2:** Core FSM, Event Sourcing, and Snapshot/Recovery mechanics.
- **Sprint 3:** Governance evaluation logic and Review cycle mechanisms.
- **Sprint 4:** LLM Provider integration and XML-based parsing logic.
- **Sprint 5 (Current):** Prompt hardening, ProviderPool credential discovery consolidation, and Benchmark Pipeline construction.

## Repository Structure
```text
karsa/
├── docs/                 # Canonical documentation
│   ├── architecture/     # Component design and overview
│   ├── implementation/   # Sprint history and audit trails
│   ├── product/          # PRD
│   ├── roadmap/          # Future milestones
│   └── vision/           # Long-term mission
├── src/
│   ├── karsa/            # Core platform code
│   │   ├── artifacts/    # Registry and projections
│   │   ├── benchmarks/   # Validation pipelines
│   │   ├── domain/       # FSM and Events
│   │   ├── governance/   # Approval logic
│   │   ├── llm/          # Prompts, ProviderManager, GeminiClient
│   │   └── workflow/     # Orchestrator and Runners
│   └── tests/            # Unit and integration tests
├── .env                  # Local secret configuration
└── pyproject.toml        # Python packaging and uv dependencies
```

## Quick Start
### Installation
Karsa uses `uv` for lightning-fast dependency management.
```bash
git clone https://github.com/your-org/karsa.git
cd karsa
uv sync
```

### Environment Setup
Karsa natively discovers credentials from your environment or a `.env` file.
Create a `.env` in the root:
```bash
GEMINI_API_KEY=your_google_api_key_here
# Alternatively, supply multiple comma-separated keys for auto-rotation:
# KARSA_GEMINI_KEYS=key1,key2,key3
```

### Running Tests
Execute the unit and integration suite:
```bash
PYTHONPATH=src uv run pytest -v
```

## Documentation
- [Vision Document](docs/vision/VISION.md)
- [Product Requirements (PRD)](docs/product/PRD.md)
- [Architecture Overview](docs/architecture/01-system-overview.md)
- [Sprint History](docs/implementation/)
- [Roadmap](docs/roadmap/ROADMAP.md)

## Roadmap
Karsa's immediate future focuses on integrating OpenAI and Anthropic natively via the Provider Layer, introducing dynamic isolated execution environments via Docker, and expanding the Benchmark Framework to measure complex multi-repository refactoring capabilities. 

## Contributing
We welcome contributions from engineers passionate about deterministic AI workflows. Please read our `docs/WORKFLOW_RULES.md` before submitting a Pull Request. All contributions must be accompanied by comprehensive tests and follow the strict `DOCUMENTATION_STYLE_GUIDE.md` conventions.
