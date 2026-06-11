import re
from karsa.review.registry import IssueRegistry
from karsa.review.models import IssueStatus
import json
import hashlib

class ReviewParsingException(Exception):
    pass

class ReviewConvergenceEngine:
    def __init__(self, registry: IssueRegistry):
        self.registry = registry
        self._last_diagnostics = None

    def process_review(self, review_text: str, cycle: int) -> dict:
        warnings = []
        issue_extraction_failed = False
        
        # 1. Update existing issues
        existing_matches = list(re.finditer(r'Issue:\s*([A-Za-z0-9\-_]+)\s*\nStatus:\s*(OPEN|PARTIALLY_RESOLVED|RESOLVED|REOPENED)', review_text))
        for match in existing_matches:
            issue_id = match.group(1).strip()
            status_str = match.group(2).strip()
            self.registry.update_status(issue_id, IssueStatus(status_str))

        # 2. Extract new issues - robust section matching
        # Handles: # New Issues, ## New Issues, ### New Issues
        # Falls back to # Confidence or end-of-text if # Summary is missing
        new_issues_section_match = re.search(r'#{1,3} New Issues(.*?)(?=#{1,3} Summary|#{1,3} Confidence|\Z)', review_text, re.DOTALL)
        extracted_new_blocking = 0
        extracted_new_non_blocking = 0
        
        if new_issues_section_match:
            new_issues_text = new_issues_section_match.group(1)
            # Robust issue extraction regex - tolerates whitespace variations
            new_issue_matches = list(re.finditer(r'Issue:\s*([A-Za-z0-9\-_]+)\s*\n+\s*Severity:\s*(BLOCKING|NON_BLOCKING)\s*\n+\s*Description:\s*\n(.*?)\n+\s*Evidence:\s*\n(.*?)(?=\n+\s*Issue:|\Z)', new_issues_text, re.DOTALL))
            for match in new_issue_matches:
                severity = match.group(2).strip()
                description = match.group(3).strip()
                evidence = match.group(4).strip()
                
                if severity == "BLOCKING":
                    extracted_new_blocking += 1
                else:
                    extracted_new_non_blocking += 1
                
                # Enforce Issue Freeze
                if cycle > 1:
                    # After cycle 1, only regressions are allowed. 
                    combined_text = (description + " " + evidence).lower()
                    if "regression" not in combined_text:
                        warnings.append(f"Dropped non-regression issue during freeze: {match.group(1).strip()}")
                        continue

                self.registry.add_issue(severity, description, evidence, cycle)
        else:
            warnings.append("Could not find '# New Issues' section. Issue extraction failed.")
            issue_extraction_failed = True

        # 3. Parser validation - detect extraction failures
        if "Severity: BLOCKING" in review_text and extracted_new_blocking == 0:
            # Check if there are existing blocking issues that were already registered
            existing_blocking_in_registry = len(self.registry.get_blocking_issues())
            if existing_blocking_in_registry == 0:
                raise ReviewParsingException(
                    "CRITICAL: Parser detected 0 blocking issues, but 'Severity: BLOCKING' was found in review text. "
                    "This indicates a parsing failure that would silently convert a REJECT into an APPROVE. "
                    "Review text contains blocking issues that the parser failed to extract."
                )

        # 4. Extract diagnostics
        review_hash = hashlib.sha256(review_text.encode('utf-8')).hexdigest()
        
        outcome_match = re.search(r'Outcome:\s*(APPROVE_WITH_CHANGES|APPROVE|REJECT)', review_text)
        detected_outcome = outcome_match.group(1) if outcome_match else "UNKNOWN"
        
        confidence_match = re.search(r'#{1,3} Confidence\s*\n\s*([0-9.]+)', review_text)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.0
        
        if confidence < 0.7:
            warnings.append(f"Low confidence ({confidence}) detected.")
            
        diagnostics = {
            "detected_outcome": detected_outcome,
            "extracted_new_blocking": extracted_new_blocking,
            "extracted_new_non_blocking": extracted_new_non_blocking,
            "parse_warnings": warnings,
            "raw_review_hash": review_hash,
            "confidence": confidence,
            "issue_extraction_failed": issue_extraction_failed
        }
        
        self._last_diagnostics = diagnostics
        
        # persist .karsa/parser_debug.json
        debug_file = self.registry.registry_file.parent / "parser_debug.json"
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        with open(debug_file, "w") as f:
            json.dump(diagnostics, f, indent=2)

        # 5. FAIL CLOSED: Never allow a failed parse to result in approval
        if issue_extraction_failed:
            # If we failed to extract issues but the review contains REJECT or BLOCKING markers,
            # this is a critical parsing failure - must not silently approve
            has_reject_marker = "Outcome: REJECT" in review_text or "Outcome:\nREJECT" in review_text
            has_blocking_marker = "Severity: BLOCKING" in review_text
            if has_reject_marker or has_blocking_marker:
                raise ReviewParsingException(
                    f"CRITICAL: Issue extraction failed but review contains rejection markers. "
                    f"has_reject={has_reject_marker}, has_blocking={has_blocking_marker}. "
                    f"Refusing to continue with empty parse result. Warnings: {warnings}"
                )

        if detected_outcome == "UNKNOWN":
            raise ReviewParsingException(
                "CRITICAL: Could not parse review outcome (APPROVE/REJECT/APPROVE_WITH_CHANGES). "
                "Parsing confidence is too low to proceed. Review text may be malformed."
            )

        if confidence < 0.7 and issue_extraction_failed:
            raise ReviewParsingException(
                f"CRITICAL: Low confidence ({confidence}) combined with issue extraction failure. "
                f"Cannot reliably determine review outcome. Warnings: {warnings}"
            )

        # Cross-check: detected REJECT with 0 blocking in registry = parsing failure
        if detected_outcome == "REJECT" and len(self.registry.get_blocking_issues()) == 0:
            # Only raise if there are also no active issues at all
            # A REJECT with all issues resolved would be unusual but possible in edge cases
            active_issues = self.registry.get_active_issues()
            if len(active_issues) == 0:
                raise ReviewParsingException(
                    "CRITICAL: Review outcome is REJECT but registry has 0 active issues. "
                    "This indicates the parser failed to extract issues from the review. "
                    "Approval must never be inferred from an empty parse result."
                )
            
        return diagnostics

    def get_metrics(self) -> dict:
        active_issues = self.registry.get_active_issues()
        blocking_count = sum(1 for i in active_issues if i.severity == "BLOCKING")
        non_blocking_count = sum(1 for i in active_issues if i.severity != "BLOCKING")
        
        all_issues = self.registry.get_all_issues()
        resolved_count = sum(1 for i in all_issues if i.status == IssueStatus.RESOLVED)
        
        return {
            "blocking_issue_count": blocking_count,
            "non_blocking_issue_count": non_blocking_count,
            "resolved_count": resolved_count
        }

    def should_approve(self) -> bool:
        metrics = self.get_metrics()
        return metrics["blocking_issue_count"] == 0

    def should_approve_safe(self, diagnostics: dict) -> bool:
        """Fail-closed approval check that considers both registry state AND parse diagnostics.
        
        Approval requires ALL of:
        1. Zero blocking issues in registry
        2. Detected outcome is not REJECT
        3. Issue extraction did not fail
        4. Parsing confidence is adequate (>= 0.7 or no issues detected)
        """
        metrics = self.get_metrics()
        
        # Must have zero blocking issues
        if metrics["blocking_issue_count"] > 0:
            return False
        
        # Detected outcome must not be REJECT
        if diagnostics.get("detected_outcome") == "REJECT":
            return False
        
        # Issue extraction must not have failed
        if diagnostics.get("issue_extraction_failed", False):
            return False
        
        # If there are parse warnings, require higher confidence
        if diagnostics.get("parse_warnings") and diagnostics.get("confidence", 0) < 0.7:
            return False
        
        return True
