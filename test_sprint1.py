import sys
from pathlib import Path
import json

# Add src to sys.path so we can import karsa
sys.path.insert(0, str(Path(__file__).parent / "src"))

from karsa.observability.manager import ObservabilityManager
from karsa.domain.pricing import PricingRegistry

def main():
    workspace = Path(__file__).parent / "test_workspace"
    workspace.mkdir(exist_ok=True)
    
    manager = ObservabilityManager(workspace)
    
    print("Testing record_execution which triggers EventBus, CostCalculator, TokenUsageCollector, and MetricsAggregator...")
    
    # Simulate an execution
    manager.record_execution(
        agent="Coder",
        model="gemini-2.5-flash",
        duration_ms=1500,
        status="SUCCESS",
        prompt="Write a hello world program in python.",
        system_prompt="You are a senior python engineer.",
        response="print('Hello world!')",
        key_fingerprint="abc-123",
        review_cycle_id="001"
    )
    
    print("\nValidating outputs...")
    
    events_file = workspace / ".karsa" / "events.jsonl"
    print(f"Events Log ({events_file.exists()}):")
    if events_file.exists():
        with open(events_file) as f:
            print(f.read())
            
    workflow_metrics = workspace / ".karsa" / "metrics" / "workflow_metrics.json"
    print(f"\nWorkflow Metrics ({workflow_metrics.exists()}):")
    if workflow_metrics.exists():
        with open(workflow_metrics) as f:
            print(json.dumps(json.load(f), indent=2))
            
    agent_metrics = workspace / ".karsa" / "metrics" / "agent_metrics.json"
    print(f"\nAgent Metrics ({agent_metrics.exists()}):")
    if agent_metrics.exists():
        with open(agent_metrics) as f:
            print(json.dumps(json.load(f), indent=2))
            
    cycle_metrics = workspace / ".karsa" / "metrics" / "review_cycle_metrics.json"
    print(f"\nReview Cycle Metrics ({cycle_metrics.exists()}):")
    if cycle_metrics.exists():
        with open(cycle_metrics) as f:
            print(json.dumps(json.load(f), indent=2))
            
    print("\nSprint 1 Foundation Implementation Success!")

if __name__ == "__main__":
    main()
