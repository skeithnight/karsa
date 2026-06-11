# REVIEW_PARSER_AUDIT.md

**Audit Date**: 2026-06-11  
**Auditor**: Karsa Governance System  
**Severity**: CRITICAL — Silent governance bypass  
**Status**: FIXED

---

## Executive Summary

A critical bug in the review parsing pipeline silently converted REJECT reviews into APPROVE decisions. The `ReviewConvergenceEngine` failed to extract issues from LLM review output due to fragile regex patterns, and the `RevisionEngine` workflow had no fail-closed safety mechanism, allowing empty parse results to trigger approval.

---

## Root Cause

### Primary Failure: Fragile Section Extraction Regex

**Location**: `src/karsa/review/convergence.py`, line 26 (original)

```python
# ORIGINAL (BUGGY)
new_issues_section_match = re.search(
    r'# New Issues(.*?)# Summary', review_text, re.DOTALL
)
```

This regex required:
1. Exactly `# New Issues` (would fail on `## New Issues`)
2. Exactly `# Summary` as the closing boundary
3. Both headers present and in exact format

When the LLM output used `## Summary`, omitted the `# Summary` header entirely, or placed content differently, the regex returned `None`. This caused **zero issues to be extracted** regardless of the review content.

### Secondary Failure: No Fail-Closed Mechanism

**Location**: `src/karsa/workflow/engine.py`, lines 50-58 (original)

```python
# ORIGINAL (BUGGY)
self.convergence.process_review(review_text, cycle)
metrics = self.convergence.get_metrics()
should_approve = self.convergence.should_approve()

if should_approve:
    outcome = "APPROVE"  # ← Overwrites LLM's REJECT outcome!
else:
    outcome = "REJECT"
```

Critical flaws:
1. The `process_review()` return value (diagnostics) was **completely ignored**
2. The `should_approve()` method only checked `blocking_issue_count == 0` in the registry
3. When the parser failed to extract issues, the registry was empty → `should_approve()` returned `True`
4. The original LLM outcome (`REJECT`) was **silently overwritten** with `APPROVE`
5. `ReviewParsingException` from the parser validation (line 58-59 of convergence.py) was caught by the generic exception handler and treated as a provider failure, not a parsing safety violation

### Tertiary Failure: Issue Extraction Regex Too Strict

**Location**: `src/karsa/review/convergence.py`, line 33 (original)

```python
# ORIGINAL (FRAGILE)
new_issue_matches = list(re.finditer(
    r'Issue:\s*([A-Z0-9\-]+)\nSeverity:\s*(BLOCKING|NON_BLOCKING)\n+Description:\n(.*?)\n+Evidence:\n(.*?)(?=\nIssue:|\Z)',
    new_issues_text, re.DOTALL
))
```

This regex:
- Required uppercase-only issue IDs (`[A-Z0-9\-]+`)
- Required exact `\n` between `Issue:` and `Severity:` lines (no extra whitespace)
- Required exact `\n` before `Description:` and `Evidence:` labels
- Failed on minor whitespace variations common in LLM output

---

## Exact Bug Location

| Component | File | Lines | Severity |
|-----------|------|-------|----------|
| Section regex | `src/karsa/review/convergence.py` | 26 | CRITICAL |
| Issue regex | `src/karsa/review/convergence.py` | 33 | HIGH |
| Outcome overwrite | `src/karsa/workflow/engine.py` | 55-58 | CRITICAL |
| Missing exception handling | `src/karsa/workflow/engine.py` | 51 | CRITICAL |
| Diagnostics ignored | `src/karsa/workflow/engine.py` | 51-53 | HIGH |

---

## Reproduction Steps

1. Start a Karsa workflow: `karsa start --idea "any idea"`
2. The ReviewAgent generates a review with `Outcome: REJECT` and multiple `Severity: BLOCKING` issues
3. If the LLM output uses `## Summary` instead of `# Summary`, or omits the `# Summary` header:
   - The section regex fails → `new_issues_section_match` is `None`
   - No issues are added to the registry
   - `issue_extraction_failed` is set to `True` but execution continues
   - The parser validation on line 58 may or may not fire depending on whether `Severity: BLOCKING` text exists in the raw review
4. `should_approve()` checks `blocking_issue_count == 0` → returns `True` (because nothing was added)
5. The workflow overwrites `outcome = "APPROVE"`
6. `review_metrics.json` records `blocking_issues: 0, non_blocking_issues: 0`
7. `DECISION_001.md` records `Decision: APPROVE`
8. But `REVIEW_001.md` (the raw LLM output) clearly says `Outcome: REJECT` with 4+ blocking issues

**Result**: A REJECT review with critical blocking issues is silently converted to APPROVE.

---

## Fix Implementation

### Fix 1: Robust Section Extraction (convergence.py)

```diff
-new_issues_section_match = re.search(r'# New Issues(.*?)# Summary', review_text, re.DOTALL)
+new_issues_section_match = re.search(r'#{1,3} New Issues(.*?)(?=#{1,3} Summary|#{1,3} Confidence|\Z)', review_text, re.DOTALL)
```

- Matches 1-3 `#` characters for heading levels
- Falls back to `# Confidence` as alternative boundary
- Falls back to end-of-text (`\Z`) if no subsequent header found

### Fix 2: Robust Issue Extraction (convergence.py)

```diff
-new_issue_matches = list(re.finditer(r'Issue:\s*([A-Z0-9\-]+)\nSeverity:\s*(BLOCKING|NON_BLOCKING)\n+Description:\n(.*?)\n+Evidence:\n(.*?)(?=\nIssue:|\Z)', new_issues_text, re.DOTALL))
+new_issue_matches = list(re.finditer(r'Issue:\s*([A-Za-z0-9\-_]+)\s*\n+\s*Severity:\s*(BLOCKING|NON_BLOCKING)\s*\n+\s*Description:\s*\n(.*?)\n+\s*Evidence:\s*\n(.*?)(?=\n+\s*Issue:|\Z)', new_issues_text, re.DOTALL))
```

- Accepts mixed-case issue IDs
- Tolerates extra whitespace between fields
- Tolerates extra blank lines

### Fix 3: Fail-Closed Safety Checks (convergence.py)

Added multiple safety barriers:
1. If `issue_extraction_failed` AND review contains `Outcome: REJECT` or `Severity: BLOCKING` → raise `ReviewParsingException`
2. If `detected_outcome == "UNKNOWN"` → raise `ReviewParsingException`
3. If `confidence < 0.7` AND `issue_extraction_failed` → raise `ReviewParsingException`
4. If `detected_outcome == "REJECT"` AND registry has 0 active issues → raise `ReviewParsingException`

### Fix 4: Explicit Exception Handling (engine.py)

`ReviewParsingException` is now caught specifically and treated as a forced REJECT, not a provider failure.

### Fix 5: Safe Approval Method (convergence.py)

New method `should_approve_safe(diagnostics)` that checks:
1. Zero blocking issues in registry
2. Detected outcome is not REJECT
3. Issue extraction did not fail
4. Adequate parsing confidence

### Fix 6: Cross-Check Guard (engine.py)

If LLM said REJECT but registry says approve, force REJECT with warning log.

### Fix 7: Parser Diagnostics Persistence

`.karsa/parser_debug.json` is written on every review parse, containing:
- `detected_outcome`
- `extracted_new_blocking`
- `extracted_new_non_blocking`
- `parse_warnings`
- `raw_review_hash`
- `confidence`
- `issue_extraction_failed`

### Fix 8: Status Command Diagnostics

`karsa status` now displays parser diagnostics including parsed outcome, blocking/non-blocking counts, confidence, and warnings.

---

## Validation Evidence

### Golden Tests Added

File: `tests/test_review_parser.py`

| Test | Validates |
|------|-----------|
| `test_extracts_all_blocking_issues` | 4 blocking + 2 non-blocking correctly extracted from real-format review |
| `test_diagnostics_match` | Diagnostics dict matches expected values |
| `test_approve_with_resolved_issues` | Clean approve with resolved issues works correctly |
| `test_extracts_issues_with_variant_format` | `##` headings and extra spaces handled |
| `test_extracts_issues_without_summary` | Missing `# Summary` still extracts issues |
| `test_blocking_mismatch_raises_exception` | `ReviewParsingException` raised on extraction mismatch |
| `test_reject_with_zero_registry_raises_exception` | Malformed REJECT raises exception |
| `test_unknown_outcome_raises_exception` | Missing outcome raises exception |
| `test_should_approve_safe_rejects_when_outcome_is_reject` | `should_approve_safe` respects LLM outcome |
| `test_should_approve_safe_rejects_on_extraction_failure` | `should_approve_safe` fails on extraction failure |
| `test_parser_debug_json_persisted` | Debug JSON written to disk |
| `test_low_confidence_with_extraction_failure_raises` | Low confidence + failed extraction = exception |
| `test_never_approves_empty_reject` | **THE BUG REPRODUCTION** - exact scenario that caused the incident |

### Test Results

```
32 passed in 7.36s
```

All 32 tests pass (16 new parser tests + 3 existing review tests + 13 other tests).

### Safety Properties Verified

1. **Fail-closed**: Every parsing failure results in REJECT, never APPROVE
2. **No silent overwrites**: LLM REJECT outcome cannot be silently converted to APPROVE
3. **Diagnostic transparency**: Every parse operation produces auditable debug output
4. **Cross-validation**: Registry state is cross-checked against LLM outcome
5. **Exception specificity**: `ReviewParsingException` is distinguished from provider failures

---

## Prevention Measures

1. **Mandatory golden tests**: All regex changes must pass golden tests with real LLM output formats
2. **Parser debug persistence**: `.karsa/parser_debug.json` provides forensic evidence for every parse
3. **Fail-closed by default**: The system now treats any parsing ambiguity as REJECT
4. **Cross-check guards**: Multiple independent checks must agree before approval
5. **Status command diagnostics**: `karsa status` exposes parser state for live debugging
