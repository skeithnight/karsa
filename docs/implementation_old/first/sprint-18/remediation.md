# Sprint-18 Capability Registry Foundation Remediation Report

## 1. Technical Debt Item Resolved

### Item A: Immutability Guard Bypass on Active Capabilities
- **Issue**: Properties of active, deprecated, retired, or revoked capability definitions could be modified directly in memory after registration, bypassing lifecycle locks.
- **Remediation**:
  - Implemented an override of `__setattr__` on `CapabilityDefinition` in `src/karsa/capabilities/domain/models.py`. Setting attributes triggers the immutability check after dataclass initialization completes (detected by the presence of `updated_at`).
  - Wrapped `dependencies` in a custom `ImmutableList` class that overrides in-place list mutations (`append`, `extend`, etc.) to delegate to the aggregate's immutability check.
  - Added read-only property verification to raise `AttributeError` for properties like `.contract` before checking lifecycle state.
  - Added comprehensive test coverage in `tests/karsa/capabilities/test_models.py` verifying draft mutations succeed, active mutations fail, and replay blocking is enforced.

## 2. Validation Status
- **Critical defects remaining**: Zero (0).
- **All tests passing**: Yes (13/13).
- **Remediation complete**: Ready for re-audit and sprint closure.
