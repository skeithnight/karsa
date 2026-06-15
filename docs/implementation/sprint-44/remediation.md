# Sprint-44 Review & Post-Mortem Foundation Remediation & Technical Debt

This document records the technical debt, unresolved warnings, and coverage status upon completion of Sprint-44.

## 1. Registered Technical Debt

### 1.1 Deprecation Warnings in Closed Sprint Code
* **Item**: Deprecation warnings regarding the usage of `datetime.datetime.utcnow()` in legacy/closed sprint review files:
  * `src/karsa/review/domain/model/review.py`
  * `src/karsa/review/application/service.py`
  * `tests/karsa/review/test_review_engine.py`
* **Impact**: Triggers deprecation warnings in Pytest outputs.
* **Remediation Plan**: These files belong to closed sprint boundaries (Sprint-42 Attribution Engine/Performance Engine Foundation). They cannot be modified in Sprint-44 due to Closed Sprint Protection constraints. They must be refactored when Sprint-42 or Sprint-43 is explicitly reopened for maintenance in future sprints.

### 1.2 Sub-90% Coverage on Prohibited Legacy Files
* **Item**: Legacy files under `src/karsa/review/` (`service.py`, `repositories.py`, `convergence.py`, etc.) show statement coverage below 90% in aggregate package analysis.
* **Impact**: Skews the overall `src/karsa/review` package coverage statistics.
* **Remediation Plan**: These are closed sprint files. Closed Sprint Protection restricts modifications or code additions to these modules. The new Sprint-44 files (`services_batch3.py`, `models.py`, `value_objects.py`, `events.py`, `lineage.py`, `postgres_repositories.py`, `repositories_batch2.py`) have passed with 100% statement and branch coverage individually, satisfying the Sprint-44 Quality Gate.

## 2. Unresolved Findings
* None. All functional and persistence requirements have been met.
