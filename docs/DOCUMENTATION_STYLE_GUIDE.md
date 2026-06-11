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

## Folder Ownership
- `architecture/`: Canonical design definitions.
- `adr/`: Architectural Decision Records.
- `roadmap/`: Planning and status tracking.
- `implementation/sprint-XX/`: The strict 4-file sprint lifecycle.
- `archive/`: Deprecated artifacts.

## Lifecycle Rules
- Architecture documents describe systems.
- Implementation documents describe work performed.
- Never mix them.
- Blueprints, reviews, inventories, summaries, status reports, migration reports, execution reports, compliance reports must be merged into canonical sprint files.

## Archival Rules
- Historical documents must be moved to `archive/` instead of deleted.
