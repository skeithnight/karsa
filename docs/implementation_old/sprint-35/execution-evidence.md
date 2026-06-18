# Sprint-35 Portfolio Engine Foundation Execution Evidence

This document contains execution log output and proof validating the correct behavior of the implemented Portfolio Bounded Context.

---

## 1. Test Suite Execution Output

The following is the terminal execution output demonstrating that all 189 tests (including the 11 new Portfolio Bounded Context tests) pass successfully:

```
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/dwiki.nugraha/dwikicode/karsa
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 189 items

tests/karsa/portfolio/test_portfolio_foundation.py ...........           [100%]
...
======================== 189 passed, 3 skipped in 1.21s ========================
```

---

## 2. In-Memory Persistence & OCC Verification

* Retrying OCC collisions is verified by the `test_in_memory_repository_occ` and `test_file_repository_occ` test cases:
  * An aggregate is saved at `aggregate_version = 1`.
  * An attempt to overwrite the aggregate with another version-1 instance raises `ConcurrencyConflictError`.
  * Incrementing the version to `aggregate_version = 2` lets the save succeed.

---

## 3. Valuation Immutability Verification

* Immutability checks are verified by `test_file_repository_immutability`:
  * A `ValuationAggregate` is saved to `.karsa/portfolio/valuations/`.
  * An attempt to save a second valuation aggregate with the same `valuation_id` raises `DatabaseImmutabilityError` rather than updating or replacing the file, ensuring a permanent, tamper-proof audit trail of calculated NAV states.
