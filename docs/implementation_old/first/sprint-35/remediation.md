# Sprint-35 Portfolio Engine Foundation Remediation Report

This document records the findings and remediation steps identified during the post-implementation audit of the Portfolio Engine Foundation.

---

## 1. Findings & Remediation Steps

* **Findings**: None
* **Remediation Requirements**: None

---

## 2. Technical Debt Register

* **DEBT-35.1 (PostgreSQL Database Migrations)**: SQL schemas are designed but not registered in active migrations. Alembic migrations and Postgres integration tests are deferred to the next evolution sprint.
* **DEBT-35.2 (utcnow deprecation warnings)**: Services and test suites use deprecated `datetime.utcnow()`. Timezone-aware UTC datetimes refactoring is deferred.
