# Sprint-50 Remediation Plan

## 1. Executive Summary
The Sprint-50 Remediation Plan directly targets the fatal deployability and environment corruption blockers identified during the Production Readiness Hostile Audit. The remediation introduces zero new business capabilities or architectural bounds. Instead, it retrofits the existing codebase with standard production containerization (`Dockerfile`, `docker-compose.yml`), cleans up orphaned legacy code imports that severed the LLM execution path, migrates test file namespaces to guarantee Pytest stability, and enforces a reproducible Python environment strategy for PostgreSQL adapters.

## 2. Findings Mapping
| Finding | Source | Remediation Strategy |
|---------|--------|----------------------|
| **F-01 Deployment Void** | `docs/implementation/sprint-50/audit.md` | Implement `Dockerfile` and `docker-compose.yml` with strict startup dependency ordering. |
| **F-02 Broken Integration** | `test_provider.py` | Strip legacy `karsa.observability.manager` imports; point `LLMClient` to new decoupled `TraceContext` emitters. |
| **F-03 Environment Failure** | `psycopg` exception | Update environment dependencies to strictly mandate `psycopg[binary]` for local/CI portability. |
| **F-04 Namespace Collision** | `pytest` Collection | Rename all colliding `test_domain_batch1.py` and `test_postgres_repository.py` files to domain-prefixed structures. |

## 3. Work Package Definitions

### WP-1: Containerization Foundation
* Create root `Dockerfile` using lightweight Python 3.9+ base image.
* Create root `docker-compose.yml` orchestrating:
  * `postgres`: The primary transactional state store.
  * `minio`: The cold storage S3-compatible backend.
  * `worker`: The primary Karsa execution engine node.
* Implement `depends_on` and Docker `healthcheck` parameters to enforce correct boot ordering (Worker must not boot before Postgres accepts connections).

### WP-2: Integration Repair
* Modify `src/karsa/llm/client.py` and `src/karsa/workflow/controller.py` to remove stale imports pointing to deleted Sprint-48/49 modules.
* Stub or repair broken legacy function calls to ensure the `PYTHONPATH=src python3 -m pytest tests` command succeeds in collecting and initializing the codebase.

### WP-3: Environment Stabilization
* Modify the local `pyproject.toml` or `uv.lock` dependency declarations (or provide explicit installation commands) ensuring `psycopg-binary` is installed natively, preventing the `libpq` C-binding compile failure on local developer machines and CI pipelines.

### WP-4: CI Namespace Correction
* Script a rename operation targeting:
  * `tests/karsa/allocation/domain/test_domain_batch1.py` -> `test_allocation_domain.py`
  * `tests/karsa/thesis/test_domain_batch1.py` -> `test_thesis_domain.py`
  * `tests/karsa/review/test_domain_batch1.py` -> `test_review_domain.py`
  * Duplicate `test_postgres_repository.py` files -> `test_risk_postgres.py`, etc.
* Ensure Pytest can collect the full AST tree without `import file mismatch` halts.

## 4. Deployment Remediation Plan
The `docker-compose.yml` will establish the minimal viable production deployment suitable for a Lenovo Tiny node, adhering to memory limits. The network topology will isolate MinIO and Postgres onto an internal bridge network, exclusively exposing the application layer.

## 5. Integration Remediation Plan
Because Observability (Sprint-49) was rewritten to passively consume standard `DomainEvent` objects, the Execution layer does not need a hard dependency on the Observability module. Remediation involves deleting the hard-coded imports in the LLM execution layer and returning to standard event emissions.

## 6. Environment Remediation Plan
Resolving the `ImportError: no pq wrapper available` requires standardizing the PostgreSQL client package. `psycopg[binary]` will be enforced as the default implementation path to eliminate compilation prerequisites on local OS bounds.

## 7. CI Stabilization Plan
Once namespaces are resolved, the full test suite must execute cleanly via `pytest`. This proves the platform can boot, compile, and mathematically execute tests across all bounded contexts simultaneously.

## 8. Risks
* Refactoring legacy paths might accidentally break older deterministic execution tests. All changes to `src/karsa` will be strictly limited to fixing `import` statements.
* Docker-compose resource limits might clash with developer environment overheads if tuned too aggressively for the home-lab spec.

## 9. Evidence Requirements
1. The physical presence of `Dockerfile` and `docker-compose.yml`.
2. Clean `docker-compose config` validation.
3. Clean `pytest --collect-only` execution demonstrating zero namespace crashes.
4. Clean `pytest` execution showing operational Postgres transactions (or correctly mocked equivalents).

## 10. Exit Criteria
The repository possesses a functional bootloader, and the continuous integration test suite completes its execution matrix without collection errors.

## 11. Final Recommendation
**READY_FOR_REMEDIATION_IMPLEMENTATION**
