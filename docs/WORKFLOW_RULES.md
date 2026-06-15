# Workflow Rules

## Purpose
This document defines the mandatory execution workflow for all planning, implementation, review, audit, and remediation work in the Karsa repository. 
The goal is to prevent documentation drift, blueprint proliferation, and repository state inconsistencies.

## Rule 1: Documentation Is The Source Of Truth
The following locations under the `docs/` root are considered authoritative:
- `docs/roadmap/`
- `docs/implementation/`
- `docs/architecture/`
- `docs/adr/`

All status reporting must reference these locations. 

The following locations are **NOT** sources of truth and are considered temporary working space only:
- `.gemini/`, `brain/`, `scratch/`, `temp/`
- Generated reports
- Ad-hoc markdown files outside the `docs/` structure

## Rule 2: No Standalone Blueprint Files
Do not create files named `blueprint.md`, `review.md`, `execution_report.md`, `status_report.md`, `summary.md`, or `assessment.md` outside the approved documentation structure. 

Planning and execution information must be merged strictly into:
- Planning → `docs/implementation/sprint-XX/plan.md`
- Implementation → `docs/implementation/sprint-XX/implementation.md`
- Audit → `docs/implementation/sprint-XX/audit.md`
- Technical debt/unresolved findings → `docs/implementation/sprint-XX/remediation.md`

## Rule 3: Sprint Lifecycle
Every standard sprint follows this strict sequence:
**PLAN → IMPLEMENT → AUDIT → REMEDIATE → CLOSE**

Required files in `docs/implementation/sprint-XX/` (where XX is a zero-padded integer):
1. `plan.md`
2. `implementation.md`
3. `audit.md`
4. `remediation.md`

No additional sprint document types are allowed.

### Rule 3.1: Emergency / Hotfix Exception
For critical, out-of-band production issues, a lightweight `docs/implementation/hotfix-XX/` folder may be created.
- It requires only `plan.md` (brief context) and `remediation.md` (post-mortem and permanent fix plan).
- The hotfix must be formally linked to and absorbed by a standard sprint lifecycle within 7 days.

## Rule 4: Evidence Before Status
A task may not be declared COMPLETE, PASS, APPROVED, or CLOSED without verifiable evidence. 
Required evidence may include (but is not limited to):
- `git diff` outputs
- Repository inspection logs
- Test execution logs
- Coverage reports
- Integration test results

## Rule 5: Documentation Closure Gate
Sprint closure is **blocked** when any of the following conditions are met:
- Extra sprint artifacts remain outside the 4 canonical files.
- Roadmap is not updated to reflect the completed work.
- ADR references in the sprint documents are inconsistent or missing.
- **No designated approver** (e.g., Tech Lead, Architect, or Engineering Manager) has explicitly approved the closure via PR review or signed checklist.

## Rule 6: Architecture Iteration Rule
Architecture drafts may exist during the active design phase. 
After architecture freeze:
- All drafts must be merged into canonical files or moved to `docs/archive/`.
- The canonical architecture must remain the single source of truth.

## Rule 7: Automated Governance Checks
All Pull Requests modifying the `docs/` directory must pass automated governance checks (via pre-commit hooks or CI pipeline):
1. **Forbidden File Check**: Fails if `blueprint.md`, `review.md`, `execution_report.md`, `status_report.md`, `summary.md`, or `assessment.md` are detected anywhere in the repo.
2. **Sprint Completeness Check**: Fails if a `docs/implementation/sprint-XX/` directory does not contain *exactly* the 4 canonical files (or 2 files for `hotfix-XX`).
3. **ADR Naming Check**: Fails if ADR files do not strictly match the regex `^ADR-\d{3}-[a-z0-9-]+\.md$`.