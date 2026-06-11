import json
import dataclasses
from pathlib import Path
from karsa.domain.models import AgentMetrics, WorkflowMetrics, ReviewCycleMetrics
from karsa.domain.events import EventBus, ExecutionCompletedEvent

class MetricsAggregator:
    def __init__(self, workspace_dir: Path):
        self.metrics_dir = workspace_dir / ".karsa" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.workflow_metrics_file = self.metrics_dir / "workflow_metrics.json"
        self.agent_metrics_file = self.metrics_dir / "agent_metrics.json"
        self.cycle_metrics_file = self.metrics_dir / "review_cycle_metrics.json"
        
        self._initialize_files()
        
        EventBus().subscribe(ExecutionCompletedEvent, self.handle_execution_completed)
        
    def _initialize_files(self):
        if not self.workflow_metrics_file.exists():
            with open(self.workflow_metrics_file, "w") as f:
                json.dump(dataclasses.asdict(WorkflowMetrics(workflow_id="default")), f, indent=2)
                
        if not self.agent_metrics_file.exists():
            with open(self.agent_metrics_file, "w") as f:
                json.dump({}, f, indent=2)
                
        if not self.cycle_metrics_file.exists():
            with open(self.cycle_metrics_file, "w") as f:
                json.dump({}, f, indent=2)

    def handle_execution_completed(self, event: ExecutionCompletedEvent):
        # Update Workflow Metrics
        with open(self.workflow_metrics_file, "r") as f:
            w_data = json.load(f)
        w_metrics = WorkflowMetrics(**w_data)
        w_metrics.total_executions += 1
        w_metrics.total_tokens += event.metrics.input_tokens + event.metrics.output_tokens
        w_metrics.total_cost_usd += event.metrics.cost_usd
        w_metrics.total_duration_ms += event.metrics.duration_ms
        with open(self.workflow_metrics_file, "w") as f:
            json.dump(dataclasses.asdict(w_metrics), f, indent=2)
            
        # Update Agent Metrics
        with open(self.agent_metrics_file, "r") as f:
            a_data = json.load(f)
        agent_name = event.metrics.agent_name
        if agent_name not in a_data:
            a_data[agent_name] = dataclasses.asdict(AgentMetrics(agent_name=agent_name))
        a_metrics = AgentMetrics(**a_data[agent_name])
        a_metrics.total_executions += 1
        a_metrics.total_tokens += event.metrics.input_tokens + event.metrics.output_tokens
        a_metrics.total_cost_usd += event.metrics.cost_usd
        a_data[agent_name] = dataclasses.asdict(a_metrics)
        with open(self.agent_metrics_file, "w") as f:
            json.dump(a_data, f, indent=2)

        # Update Review Cycle Metrics
        with open(self.cycle_metrics_file, "r") as f:
            c_data = json.load(f)
        cycle_id = str(event.metrics.review_cycle_id)
        if cycle_id not in c_data:
            c_data[cycle_id] = dataclasses.asdict(ReviewCycleMetrics(review_cycle_id=cycle_id))
        c_metrics = ReviewCycleMetrics(**c_data[cycle_id])
        c_metrics.total_executions += 1
        c_metrics.total_tokens += event.metrics.input_tokens + event.metrics.output_tokens
        c_metrics.total_cost_usd += event.metrics.cost_usd
        c_data[cycle_id] = dataclasses.asdict(c_metrics)
        with open(self.cycle_metrics_file, "w") as f:
            json.dump(c_data, f, indent=2)
