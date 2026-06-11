---
status: active
owner: Karsa Architecture Team
created: 2026-06-11
last_reviewed: 2026-06-11
next_review: 2026-09-11
---

# Documentation Review Policy

To ensure documentation remains accurate and actionable, the following review cadences are strictly enforced based on artifact type:

## Architecture Documents
- **Cadence**: Quarterly
- **Policy**: Canonical architecture (`01` through `05`) must be verified against current implementation state every 3 months. If drift is detected, an ADR must be raised or the code refactored.

## Architectural Decision Records (ADRs)
- **Cadence**: Annually
- **Policy**: ADRs capture historical context. They do not require frequent updates, but should be audited annually to ensure superseded ADRs are marked as deprecated.

## Roadmap & Project Dashboards
- **Cadence**: Every Sprint
- **Policy**: The `ROADMAP.md`, `PROJECT_DASHBOARD.md`, and `TRACEABILITY_MATRIX.md` must be explicitly updated at the beginning and end of every sprint boundary.

## Reports & Audits
- **Cadence**: Never (Immutable)
- **Policy**: Sprint remediation reports and audits capture a point-in-time state. Once published to `docs/reports/` or `docs/sprint-XX/audits/`, they may never be edited. If they are wrong, a new addendum report must be filed.
