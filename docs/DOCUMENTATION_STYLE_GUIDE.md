# Documentation Style Guide

## Naming Conventions
- **Architecture files**: `01-system-overview.md` (lowercase, kebab-case, sequentially numbered).
- **ADRs**: `ADR-001-description.md` (ADR-XXX prefix, zero-padded to 3 digits, lowercase kebab-case description).
- **Roadmap files**: `roadmap-2024-q1.md` (must include timeboxing, e.g., YYYY-QX or YYYY-MM).
- **Sprint files**: Strictly `plan.md`, `implementation.md`, `audit.md`, `remediation.md` (lowercase).
- **Hotfix files**: `plan.md`, `remediation.md` (only for emergency workflows).

## Allowed Document Types
- Architecture definitions
- Architectural Decision Records (ADRs)
- Roadmap and status tracking
- Sprint lifecycle documents (4 canonical files)
- Emergency hotfix documents (2 canonical files)

## Directory Enforcement
All documentation must reside under the `docs/` root directory. Allowed subdirectories are strictly:
- `docs/architecture/`
- `docs/adr/`
- `docs/roadmap/`
- `docs/implementation/`
- `docs/archive/`

All other directories at the repository root or within `docs/` are prohibited.

## Folder Ownership
- `docs/architecture/`: Canonical design definitions.
- `docs/adr/`: Architectural Decision Records.
- `docs/roadmap/`: Planning and status tracking.
- `docs/implementation/sprint-XX/`: The strict 4-file sprint lifecycle (XX = zero-padded integer, e.g., `sprint-01`).
- `docs/implementation/hotfix-XX/`: Emergency 2-file lifecycle for critical production issues.
- `docs/archive/`: Deprecated or historical artifacts.

## ADR Governance & Lifecycle
- ADR numbers must be unique. Duplicate ADR identifiers are prohibited.
- Every ADR must include the following metadata block at the top of the file:
  ```markdown
  - **Status**: [ Proposed | Accepted | Superseded | Deprecated ]
  - **Date**: YYYY-MM-DD
  - **Supersedes**: N/A (or ADR-XXX)
  - **Superseded By**: N/A (or ADR-XXX)

## Traceability Requirements
- `plan.md` and `implementation.md` must include a "References" section explicitly linking to the relevant `docs/adr/`, `docs/architecture/`, and `docs/roadmap/` files they are executing.

## Lifecycle Rules
- Architecture documents describe systems.
- Implementation documents describe work performed.
- Never mix them.

## Sprint Artifact Consolidation
Upon sprint closure, all temporary or auxiliary files (e.g., blueprint files, challenge files, review files, execution packages) must be merged into the 4 canonical sprint lifecycle files. Standalone artifacts are prohibited.

## Archival Rules
- Historical or deprecated documents must be moved to `docs/archive/` with a clear note on why they were archived, instead of being deleted. This preserves institutional knowledge.
