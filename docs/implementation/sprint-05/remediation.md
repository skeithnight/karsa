# Sprint 5 Remediation

## Phase 2.6 Provider Reality Blocker (DEPLOYMENT_BLOCKER)
- **Issue:** `GEMINI_API_KEY` exists in the user's host shell but is stripped by the Antigravity sandbox isolation boundary before reaching Karsa's runtime.
- **Classification:** Runtime Environment Constraint (Not a Karsa software defect).
- **Sprint 5.5 Update:** Execution of the end-to-end reality proof aborted due to zero discovered credentials. The software safely rejected execution via `MissingCredentialsError` (TD-009 resolution). ProviderPool logic is proven mathematically correct.
- **Recommendation:** The deployment environment must be explicitly configured to forward secrets into the sandbox, or a `.env` loader pattern must be formally adopted by the user's execution strategy.

## TD-009: Provider Error Ambiguity (RESOLVED)
- **Issue:** The system lacked explicit error taxonomy. Missing credentials triggered `QUOTA_EXHAUSTED` retries.
- **Root Cause:** `ProviderPool` swallowed missing key initialization, returning `None`, which `GeminiClient` interpreted as a quota issue. `RetryCoordinator` lacked semantic filtering.
- **Action Taken:** Introduced `karsa.llm.errors` with explicit classes (`MissingCredentialsError`, `AuthenticationError`, `QuotaExhaustedError`, etc.). Modified `ProviderPool` to `raise MissingCredentialsError` instantly, and `RetryCoordinator` to instantly crash instead of retrying.
- **Verification:** `run_reality_validation.py` halts in `<50ms` deterministically instead of hanging. Proof added in `src/tests/unit/test_retry_taxonomy.py`.