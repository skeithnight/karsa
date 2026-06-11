from typing import Dict, List
from karsa.review.models import Issue, IssueStatus
import json
from pathlib import Path

class IssueRegistry:
    def __init__(self, workspace_dir: Path):
        self.registry_file = workspace_dir / ".karsa" / "issues.json"
        self.issues: Dict[str, Issue] = {}
        self.load()

    def load(self):
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                for item in data:
                    self.issues[item["id"]] = Issue(
                        id=item["id"],
                        severity=item["severity"],
                        description=item["description"],
                        evidence=item["evidence"],
                        status=IssueStatus(item["status"]),
                        cycle_introduced=item["cycle_introduced"]
                    )

    def save(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "id": issue.id,
                "severity": issue.severity,
                "description": issue.description,
                "evidence": issue.evidence,
                "status": issue.status.value,
                "cycle_introduced": issue.cycle_introduced
            }
            for issue in self.issues.values()
        ]
        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_issue(self, severity: str, description: str, evidence: str, cycle: int) -> str:
        count = len(self.issues) + 1
        prefix = "P" if severity.upper() == "BLOCKING" else "N"
        issue_id = f"{prefix}{count:03d}"
        
        self.issues[issue_id] = Issue(
            id=issue_id,
            severity=severity.upper(),
            description=description,
            evidence=evidence,
            status=IssueStatus.OPEN,
            cycle_introduced=cycle
        )
        self.save()
        return issue_id

    def update_status(self, issue_id: str, new_status: IssueStatus):
        if issue_id in self.issues:
            self.issues[issue_id].status = new_status
            self.save()

    def get_active_issues(self) -> List[Issue]:
        return [issue for issue in self.issues.values() if issue.status in (IssueStatus.OPEN, IssueStatus.PARTIALLY_RESOLVED, IssueStatus.REOPENED)]

    def get_blocking_issues(self) -> List[Issue]:
        return [issue for issue in self.get_active_issues() if issue.severity == "BLOCKING"]

    def get_all_issues(self) -> List[Issue]:
        return list(self.issues.values())
