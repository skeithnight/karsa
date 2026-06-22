# Sprint-16 Remediation & Technical Debt Document

## 1. Technical Debt Items

### Item A: Missing `pytest-cov` Package
- **Issue**: The virtual environment lacks the `pytest-cov` package, making automated command-line code coverage verification via `pytest --cov` impossible.
- **Cascading impact**: Local developer coverage validation requires manual check or local package installation.
- **Remediation Plan**: Include `pytest-cov>=4.1.0` in the `[dependency-groups] dev` block in `pyproject.toml` during Sprint-17 setup.

### Item B: Datetime Deprecation Warnings
- **Issue**: Pytest logs deprecation warnings concerning `datetime.datetime.utcnow()` being deprecated in Python 3.12+ and scheduled for removal.
- **Code Reference**:
  - `src/karsa/capabilities/domain/models.py:85`
  - `src/karsa/capabilities/domain/models.py:105`
  - `src/karsa/capabilities/domain/models.py:129`
- **Remediation Plan**: Refactor all datetimes to use timezone-aware structures: `datetime.now(datetime.timezone.utc)`. This will be done in the clean-up phase or during the next sprint's workspace initialization.

---

## 2. Validation Status
- **Critical defects remaining**: Zero (0).
- **All tests passing**: Yes (11/11).
- **Remediation complete**: Ready for sprint closure.
