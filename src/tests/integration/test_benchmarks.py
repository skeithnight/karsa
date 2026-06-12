import pytest
import os
import tempfile
from pathlib import Path

from karsa.benchmarks.models import BenchmarkDefinition
from karsa.benchmarks.runner import BenchmarkSuiteRunner

class MockProviderManager:
    def __init__(self):
        self.calls = 0
        
    def generate(self, prompt: str) -> str:
        self.calls += 1
        if "Product Engineer" in prompt:
            return """<file path="main.py">
def test_fn(): pass
</file>
<file path="test_main.py">
def test_fn_test(): pass
</file>
"""
        elif "Review Agent" in prompt:
            if self.calls <= 2:
                return '{"decision": "REVISE", "convergence_score": 0.5, "blocking_issues": ["No content"]}'
            return '{"decision": "APPROVED", "convergence_score": 1.0, "blocking_issues": []}'
        return ""

def test_benchmark_framework():
    provider = MockProviderManager()
    runner = BenchmarkSuiteRunner(provider)
    
    benchmark = BenchmarkDefinition(
        benchmark_id="bm_001",
        benchmark_name="Test Benchmark",
        objective="Create a simple test",
        expected_artifacts=[],
        success_criteria=[]
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "results"
        
        results_data = runner.execute_suite([benchmark])
        
        assert len(results_data["results"]) == 1
        res = results_data["results"][0]
        assert res["benchmark_id"] == "bm_001"
        assert res["state"] == "APPROVED"
        assert res["review_cycles"] > 0
        assert "main.py" in res["generated_files"]
        assert "test_main.py" in res["generated_files"]
        
        runner.export_results(results_data, out_dir=str(out_dir))
        
        assert (out_dir / "benchmark_results.json").exists()
        assert (out_dir / "benchmark_results.md").exists()
