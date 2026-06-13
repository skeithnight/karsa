# Documentation Style Guide

## Naming Conventions
- Architecture files: `01-system-overview.md` (lowercase, kebab-case, numbered)
- ADRs: `ADR-001-description.md` (ADR-XXX prefix)
- Sprint files: strictly `plan.md`, `implementation.md`, `audit.md`, `remediation.md` (lowercase)

## Allowed Document Types
- Architecture definitions
- Architectural Decision Records (ADRs)
- Roadmap
- Sprint lifecycle documents

## Directory Enforcement
Allowed root directories:
- `architecture`
- `adr`
- `roadmap`
- `implementation`
- `archive`

All others prohibited.

## Folder Ownership
- `architecture/`: Canonical design definitions.
- `adr/`: Architectural Decision Records.
- `roadmap/`: Planning and status tracking.
- `implementation/sprint-XX/`: The strict 4-file sprint lifecycle.
- `archive/`: Deprecated artifacts.

## ADR Number Governance
- ADR numbers must be unique.
- Duplicate ADR identifiers prohibited.

## Lifecycle Rules
- Architecture documents describe systems.
- Implementation documents describe work performed.
- Never mix them.

## Sprint Artifact Consolidation
Upon sprint closure:
- all blueprint files
- all challenge files
- all review files
- all execution packages
must be merged into canonical sprint lifecycle files.

## Archival Rules
- Historical documents must be moved to `archive/` instead of deleted.
