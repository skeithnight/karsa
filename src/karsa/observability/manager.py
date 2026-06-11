import json
from pathlib import Path
from datetime import datetime, timezone
from karsa.observability.trace import TraceLogger, get_iso_timestamp
from karsa.observability.diff import ArtifactDiffTracker
from karsa.observability.metrics import ReviewMetricsTracker

class ObservabilityManager:
    def __init__(self, workspace_dir: Path):
        self.karsa_dir = workspace_dir / ".karsa"
        self.karsa_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.karsa_dir / "execution.log"
        self.executions_dir = self.karsa_dir / "executions"
        self.executions_dir.mkdir(exist_ok=True)
        
        self.decisions_dir = self.karsa_dir / "decisions"
        self.decisions_dir.mkdir(exist_ok=True)
        
        self.timeline_file = self.karsa_dir / "timeline.json"
        if not self.timeline_file.exists():
            with open(self.timeline_file, "w") as f:
                json.dump([], f)

        self.trace_logger = TraceLogger(workspace_dir)
        self.diff_tracker = ArtifactDiffTracker(workspace_dir)
        self.metrics_tracker = ReviewMetricsTracker(workspace_dir)

    def log_trace(self, event_name: str):
        self.trace_logger.log_event(event_name)

    def log_execution(self, agent: str, action: str, status: str, duration_ms: int):
        timestamp = get_iso_timestamp()
        log_entry = f"[{timestamp}] {agent} {action} - Status: {status} ({duration_ms}ms)\n"
        with open(self.log_file, "a") as f:
            f.write(log_entry)

    def record_execution(self, agent: str, model: str, duration_ms: int, status: str, prompt: str, system_prompt: str, response: str, key_fingerprint: str = "none", review_cycle_id: str = "001"):
        count = len(list(self.executions_dir.glob("*"))) + 1
        exec_id = f"{count:04d}"
        exec_dir = self.executions_dir / exec_id
        exec_dir.mkdir(exist_ok=True)
        
        # Calculate prompt_hash and char counts
        import hashlib
        import dataclasses
        from karsa.domain.models import ExecutionMetrics
        from karsa.domain.events import EventBus, ExecutionCompletedEvent
        from karsa.domain.pricing import PricingRegistry, CostCalculator
        from karsa.observability.collector import TokenUsageCollector
        from karsa.observability.aggregator import MetricsAggregator
        
        # Initialize EventBus and Aggregator lazily for MVP
        global_karsa_dir = Path.home() / ".karsa"
        events_file = self.karsa_dir / "events.jsonl"
        
        if getattr(EventBus(), "_events_log_file", None) is None:
            EventBus().initialize(events_file)
            # Boot up the aggregator
            MetricsAggregator(self.karsa_dir.parent)
            
        full_prompt = f"System:\n{system_prompt}\n\nPrompt:\n{prompt}"
        prompt_hash = hashlib.sha256(full_prompt.encode('utf-8')).hexdigest()
        input_chars = len(full_prompt)
        output_chars = len(response)
        
        input_tokens, in_conf = TokenUsageCollector.estimate_tokens(model, full_prompt)
        output_tokens, out_conf = TokenUsageCollector.estimate_tokens(model, response)
        confidence = "LOW" if in_conf == "LOW" or out_conf == "LOW" else "HIGH"
        
        registry = PricingRegistry(global_karsa_dir / "pricing.json")
        calculator = CostCalculator(registry)
        cost_usd = calculator.calculate_usd(model, input_tokens, output_tokens)
        
        metrics = ExecutionMetrics(
            execution_id=exec_id,
            review_cycle_id=review_cycle_id,
            agent_name=agent,
            model=model,
            provider="karsa-llm",
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_estimation_confidence=confidence,
            cost_usd=cost_usd,
            status=status,
            timestamp=get_iso_timestamp()
        )
        
        with open(exec_dir / "execution_metrics.json", "w") as f:
            json.dump(dataclasses.asdict(metrics), f, indent=2)
        
        metadata = {
            "execution_id": exec_id,
            "agent_name": agent,
            "model": model,
            "key_fingerprint": key_fingerprint,
            "provider": "karsa-llm",
            "duration_ms": duration_ms,
            "timestamp": metrics.timestamp,
            "started_at": metrics.timestamp, # approximated
            "completed_at": metrics.timestamp,
            "input_chars": input_chars,
            "output_chars": output_chars,
            "prompt_hash": prompt_hash,
            "status": status
        }
        with open(exec_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
        with open(exec_dir / "request.txt", "w") as f:
            f.write(full_prompt)
            
        with open(exec_dir / "response.txt", "w") as f:
            f.write(response)
            
        EventBus().publish(ExecutionCompletedEvent(metrics=metrics))

    def record_decision(self, agent: str, decision: str, reason: str, evidence: str, confidence: float, provider: str = "unknown", key_fingerprint: str = "none", source: str = "karsa-agent"):
        count = len(list(self.decisions_dir.glob("*.md"))) + 1
        decision_id = f"{count:03d}"
        filepath = self.decisions_dir / f"DECISION_{decision_id}.md"
        
        content = (
            f"Decision ID: {decision_id}\n\n"
            f"Agent: {agent}\n\n"
            f"Decision: {decision}\n\n"
            f"Reason:\n{reason}\n\n"
            f"Evidence:\n{evidence}\n\n"
            f"Provider: {provider}\n\n"
            f"Key Fingerprint: {key_fingerprint}\n\n"
            f"Source: {source}\n\n"
            f"Confidence: {confidence}\n\n"
            f"Timestamp: {get_iso_timestamp()}\n"
        )
        with open(filepath, "w") as f:
            f.write(content)

    def track_timeline(self, agent: str, duration_ms: int):
        with open(self.timeline_file, "r") as f:
            timeline = json.load(f)
        
        timeline.append({
            "agent": agent,
            "duration_ms": duration_ms,
            "timestamp": get_iso_timestamp()
        })
        
        with open(self.timeline_file, "w") as f:
            json.dump(timeline, f, indent=2)        

    def get_status_info(self):
        execution_count = 0
        total_runtime = 0
        current_model = "unknown"
        last_activity = "N/A"
        
        if self.timeline_file.exists():
            with open(self.timeline_file, "r") as f:
                timeline = json.load(f)
                execution_count = len(timeline)
                total_runtime = sum(t.get("duration_ms", 0) for t in timeline)
                if timeline:
                    last_activity = timeline[-1].get("timestamp", "N/A")
        
        if self.executions_dir.exists():
            execs = sorted(list(self.executions_dir.glob("*")))
            if execs:
                meta_file = execs[-1] / "metadata.json"
                if meta_file.exists():
                    with open(meta_file, "r") as f:
                        meta = json.load(f)
                        current_model = meta.get("model", "unknown")
                        
        latest_decision = "NONE"
        if self.decisions_dir.exists():
            decisions = sorted(list(self.decisions_dir.glob("*.md")))
            if decisions:
                with open(decisions[-1], "r") as f:
                    content = f.read()
                    import re
                    match = re.search(r'Decision:\s*(.+)', content)
                    if match:
                        latest_decision = match.group(1).strip()
                        
        revision_count = 0
        revisions_dir = self.karsa_dir.parent / "docs" / "revisions"
        if revisions_dir.exists():
            revision_count = len(list(revisions_dir.glob("*.md")))
            
        metrics = self.metrics_tracker.get_latest_metrics()
        blocking = metrics.get("blocking_issues", 0)
        non_blocking = metrics.get("non_blocking_issues", 0)
        resolved = metrics.get("resolved_issues", 0)
        convergence_score = metrics.get("convergence_score", 0)
        
        provider_health = "UNKNOWN"
        current_prov = current_model
        retry_count = 0
        fallback_count = 0
        last_error = "None"
        current_key = "none"
        quota_failures = 0
        last_failure_timestamp = "N/A"
        
        provider_file = self.karsa_dir / "provider.json"
        if provider_file.exists():
            with open(provider_file, "r") as f:
                p_data = json.load(f)
                provider_health = p_data.get("health", "UNKNOWN")
                current_prov = p_data.get("current_provider", current_model)
                retry_count = p_data.get("retry_count", 0)
                fallback_count = p_data.get("fallback_count", 0)
                last_error = p_data.get("last_error", "None")
                current_key = p_data.get("current_key", "none")
                quota_failures = p_data.get("quota_failures", 0)
                last_failure_timestamp = p_data.get("last_failure_timestamp", "N/A")
            
        return {
            "execution_count": execution_count,
            "total_runtime": total_runtime,
            "current_model": current_model,
            "latest_decision": latest_decision,
            "revision_count": revision_count,
            "last_activity": last_activity,
            "blocking": blocking,
            "non_blocking": non_blocking,
            "resolved": resolved,
            "convergence_score": f"{'+' if convergence_score > 0 else ''}{convergence_score}",
            "provider_health": provider_health,
            "current_provider": current_prov,
            "retry_count": retry_count,
            "fallback_count": fallback_count,
            "last_error": last_error,
            "current_key": current_key,
            "quota_failures": quota_failures,
            "last_failure_timestamp": last_failure_timestamp
        }
        
    def update_provider_status(self, health: str, current_provider: str, current_key: str, retry_count: int, fallback_count: int, quota_failures: int, last_error: str, last_failure_timestamp: str = "N/A"):
        provider_file = self.karsa_dir / "provider.json"
        data = {
            "health": health,
            "current_provider": current_provider,
            "current_key": current_key,
            "retry_count": retry_count,
            "fallback_count": fallback_count,
            "quota_failures": quota_failures,
            "last_error": last_error,
            "last_failure_timestamp": last_failure_timestamp
        }
        with open(provider_file, "w") as f:
            json.dump(data, f, indent=2)
