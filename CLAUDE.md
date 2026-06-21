# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Karsa is an Enterprise Autonomous AI Orchestration Framework & Virtual Investment Firm Console. Two subsystems:

- **Backend**: Python 3.12+ / FastAPI orchestration framework (`src/karsa/`)
- **Frontend**: Next.js 16.2.9 / React 19 / TypeScript (`karsa-web/`)

## Development Commands

### Backend (Python, uses `uv` package manager)

```bash
uv sync                                          # Install dependencies
uv run uvicorn karsa.app:app --host 0.0.0.0 --port 8000  # Run API server
uv run alembic upgrade head                      # Run database migrations
uv run karsa start --idea "my idea"              # Run CLI
uv run pytest tests/                             # Run all tests
uv run pytest tests/unit/                        # Run unit tests only
uv run pytest tests/integration/                 # Run integration tests only
uv run pytest tests/path/to/test_file.py::test_name  # Run single test
```

### Frontend (karsa-web/)

```bash
cd karsa-web
npm install                  # Install dependencies
npm run dev                  # Dev server (localhost:3000)
npm run build                # Production build (static export)
npm run test                 # Run tests (vitest)
npm run lint                 # Lint (eslint)
npx tsc --noEmit             # Type check
```

### Docker (full stack)

```bash
docker compose up            # postgres + minio + karsa-api + karsa-web + workers
```

Services: postgres (5432), minio, karsa-api (8000), karsa-web (3000), karsa-projection-worker, karsa-bootstrap-producer, karsa-cio-producer.

## Architecture

### Backend: Domain-Driven Design + Event Sourcing

Every bounded context in `src/karsa/<module>/` follows the same layered structure:

```
<module>/
  api.py or api/          # FastAPI routes, DTOs, mappers
  application/            # Application services, command/query handlers
  domain/                 # Domain models, events, value objects, repository ports
  infrastructure/         # Postgres repositories, adapters, event buses
  projections/            # Read model projections (CQRS read side)
```

Key patterns:
- **Event Sourcing**: All state transitions emit immutable domain events. The `workflow/` module implements the FSM (IDEA -> DRAFT -> REVIEW -> ...).
- **CQRS**: Separate write models (aggregates) and read models (projections). Transactional outbox for reliable event publishing.
- **Ports & Adapters**: `ports.py` files define interfaces; `infrastructure/` provides Postgres, in-memory, and file-based adapters.
- **DI Container**: `bootstrap.py` in each module wires dependencies via `ApplicationContainer`.

Major modules: `allocation/`, `attribution/`, `attribution_engine/`, `cio/`, `risk/`, `execution/`, `thesis/`, `review/`, `review_engine/`, `portfolio/`, `governance/`, `governance_engine/`, `performance/`, `performance_engine/`, `post_mortem/`, `decision_journal/`, `regime/`, `memory/`, `providers/`, `llm/`, `workflow/`, `shared/`, `firm_intelligence/`, `market/`, `capabilities/`, `evidence/`.

Shared DDD building blocks live in `src/karsa/shared/` (aggregates, events, UoW, URN, persistence).

### Frontend: DTO -> Mapper -> ViewModel Pipeline

Data flow: API response (DTO) -> defensive mapper (coalesces nulls) -> ViewModel -> UI component.

Each feature module in `karsa-web/src/features/<feature>/` has:
- `types/viewmodels.ts` — ViewModel type definitions
- `utils/mappers.ts` — DTO to ViewModel mappers
- `utils/__tests__/` — Mapper unit tests

Key frontend stack: TanStack Query v5 (data fetching), Zustand (UI state), AG Grid (tables), Recharts (charts), shadcn/ui (components), Tailwind CSS v4.

Path alias: `@/*` maps to `karsa-web/src/*`.

### Multi-Service Architecture

Docker Compose orchestrates separate containers for API, web console, projection worker, bootstrap producer, and CIO producer. PostgreSQL is the shared event store and message bus (`PostgresEventBus`).

## Governance (Mandatory)

Before generating output, comply with:
- `docs/DOCUMENTATION_STYLE_GUIDE.md` — naming, directory rules, ADR format
- `docs/WORKFLOW_RULES.md` — sprint lifecycle, evidence requirements, documentation gates
- `docs/ENGINEERING_STANDARDS.md` — commit traceability, QA thresholds, security policy
- `docs/roadmap/ROADMAP.md` — current planning status

### Pre-Output Verification

1. **Naming Conventions**: Check variable, file, and function naming standards before writing.
2. **Directory Structures**: Place code and assets in the correct folders per the style guide.
3. **Evidence**: Back all technical decisions with project data or explicit requirements.
4. **Conflicts**: If a request contradicts the governance docs, flag the conflict before writing code.

### Commit Messages

Reference sprint or ADR: `feat(auth): implement OAuth2 - refs ADR-005, sprint-02`

### Sprint Lifecycle

Every sprint follows: DESIGN -> AUDIT -> REMEDIATION -> IMPLEMENT -> AUDIT -> REMEDIATION -> VERIFY -> DONE

Canonical files in `docs/implementation/sprint-XX/`: `design.md`, `implementation.md`, `audit.md`, `remediation.md`, `verify.md`.

## Next.js Warning

Next.js 16.2.9 has breaking changes from training data. Before writing frontend code, read the relevant guide in `node_modules/next/dist/docs/`. Heed deprecation notices.

## RTK (Token Optimization)

Prefix shell commands with `rtk` for 60-90% token savings on dev operations (handled automatically by hook). See `.agents/rules/antigravity-rtk-rules.md`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

# graphify
- **graphify** (`.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.
