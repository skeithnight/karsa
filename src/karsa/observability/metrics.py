from pathlib import Path
import json

class ReviewMetricsTracker:
    def __init__(self, workspace_dir: Path):
        self.metrics_file = workspace_dir / ".karsa" / "review_metrics.json"
        if not self.metrics_file.exists():
            with open(self.metrics_file, "w") as f:
                json.dump([], f)

    def record_metrics(self, cycle: int, blocking: int, non_blocking: int, resolved: int, new: int, convergence_score: int):
        with open(self.metrics_file, "r") as f:
            metrics = json.load(f)
            
        metrics.append({
            "review_cycle": cycle,
            "blocking_issues": blocking,
            "non_blocking_issues": non_blocking,
            "resolved_issues": resolved,
            "new_issues": new,
            "convergence_score": convergence_score
        })
        
        with open(self.metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

    def get_latest_metrics(self) -> dict:
        if self.metrics_file.exists():
            with open(self.metrics_file, "r") as f:
                metrics = json.load(f)
                if metrics:
                    return metrics[-1]
        return {}
