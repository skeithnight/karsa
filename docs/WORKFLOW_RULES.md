# Workflow Rules

## Purpose

This document defines the mandatory execution workflow for all planning, implementation, review, audit, and remediation work in the Karsa repository.

The goal is to prevent documentation drift, blueprint proliferation, and repository state inconsistencies.

---

# Rule 1: Documentation Is The Source Of Truth

The following locations are considered authoritative:

- docs/roadmap/
- docs/implementation/
- docs/architecture/
- docs/adr/

All status reporting must reference these locations.

The following locations are NOT sources of truth:

- .gemini/
- brain/
- scratch/
- temp/
- generated reports
- ad-hoc markdown files

These locations are considered temporary working space only.

---

# Rule 2: No Standalone Blueprint Files

Do not create:

- blueprint.md
- review.md
- execution_report.md
- status_report.md
- summary.md
- assessment.md

outside the approved documentation structure.

Planning information must be merged into:

docs/implementation/sprint-XX/plan.md

Implementation information must be merged into:

docs/implementation/sprint-XX/implementation.md

Audit information must be merged into:

docs/implementation/sprint-XX/audit.md

Technical debt and unresolved findings must be merged into:

docs/implementation/sprint-XX/remediation.md

---

# Rule 3: Sprint Lifecycle

Every sprint follows:

PLAN
→ IMPLEMENT
→ AUDIT
→ REMEDIATE
→ CLOSE

Required files:

docs/implementation/sprint-XX/

- plan.md
- implementation.md
- audit.md
- remediation.md

No additional sprint document types are allowed.

---

# Rule 4: Evidence Before Status

A task may not be declared COMPLETE, PASS, APPROVED, or CLOSED without evidence.

Required evidence may include:

- git diff
- repository inspection
- test execution
- coverage report
- integration test results

Accepted format:

Claim
Evidence
Result

If evidence is unavailable:

Status = UNVERIFIED

---

# Rule 5: Documentation Must Be Updated

Every completed task must update documentation.

Before declaring completion:

1. Update sprint documentation.
2. Update roadmap if sprint status changes.
3. Verify documentation changes.

Required verification:

git diff --name-only docs/

Completion reports must show documentation updates.

If documentation was not updated:

Status = INCOMPLETE

---

# Rule 6: Architecture Freeze Protection

When architecture is marked frozen:

Do not:

- redesign architecture
- create new orchestration layers
- introduce new core subsystems
- replace existing foundations

unless explicitly approved through a documented architecture decision.

Prefer implementation and capability delivery over architectural expansion.

---

# Rule 7: Technical Debt Handling

Technical debt must be recorded.

Do not block sprint closure for:

- low-risk cleanup
- coverage improvements
- cosmetic refactors

unless they are production blockers.

All deferred work must be tracked in:

remediation.md

---

# Rule 8: Sprint Closure Criteria

A sprint may be closed only when:

- code is implemented
- tests pass
- documentation is updated
- audit is completed
- remaining debt is recorded

Closure status:

COMPLETE
COMPLETE_WITH_KNOWN_DEBT
NOT_COMPLETE

Use the most conservative status supported by evidence.