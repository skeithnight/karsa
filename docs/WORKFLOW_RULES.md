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

---

# Rule 5: Documentation Closure Gate

Sprint closure is blocked when:

* extra sprint artifacts remain
* roadmap not updated
* ADR references inconsistent

---

# Rule 6: Architecture Iteration Rule

Architecture drafts may exist during design.

After architecture freeze:

drafts must be merged or archived.

Canonical architecture remains single-source.