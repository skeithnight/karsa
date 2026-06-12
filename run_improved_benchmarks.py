import os
import sys
from karsa.benchmarks.models import BenchmarkDefinition
from karsa.benchmarks.runner import BenchmarkSuiteRunner

class MockImprovedProvider:
    def __init__(self):
        self.calls = {}
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        prompt = prompt or system_prompt
        # Check if the prompt has the new improved strict gates
        is_improved_pe = "test_*.py" in prompt and "README.md" in prompt and "Edge Case Coverage" in prompt
        is_improved_review = "Exit code: 5" in prompt and "REVISE" in prompt and "APPROVED" in prompt
        
        if "Product Engineer" in prompt:
            if is_improved_pe:
                # Generates the correct files
                return """<file path="main.py">
def do_work(): pass
</file>
<file path="test_main.py">
def test_do_work(): pass
</file>
<file path="README.md">
# Project
</file>"""
            else:
                return """<file path="main.py">
def do_work(): pass
</file>"""
        elif "Review Agent" in prompt:
            if is_improved_review:
                # Look at the tool output or assume if we have tests we pass
                if "test_main.py" in prompt or "def test_do_work" in prompt or "Exit code: 0" in prompt:
                    return '{"decision": "APPROVED", "convergence_score": 1.0, "blocking_issues": []}'
                else:
                    return '{"decision": "REVISE", "convergence_score": 0.5, "blocking_issues": ["Missing tests"]}'
            else:
                return '{"decision": "REVISE", "convergence_score": 0.5, "blocking_issues": ["No test found"]}'
        return ""

def main():
    provider_manager = MockImprovedProvider()
    runner = BenchmarkSuiteRunner(provider_manager)
    
    benchmarks = [
        BenchmarkDefinition(
            benchmark_id="bm_001_duplicate_finder_improved",
            benchmark_name="Duplicate File Finder CLI",
            objective="Build a Python CLI duplicate file finder that uses SHA-256 to find duplicates in a directory. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_002_expense_tracker_improved",
            benchmark_name="Expense Tracker CLI",
            objective="Build a Python Expense Tracker CLI using sqlite3 to add, list, and summarize expenses. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_003_todo_api_improved",
            benchmark_name="Todo REST API",
            objective="Build a Python Todo REST API using the http.server standard library (do not use Flask/FastAPI). Include memory persistence and full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_004_static_site_improved",
            benchmark_name="Markdown Static Site Generator",
            objective="Build a Python tool to convert a folder of .md files into .html files. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_005_csv_analysis_improved",
            benchmark_name="CSV Data Analysis Utility",
            objective="Build a Python CSV Data Analysis Utility that reads a dataset, calculates min/max/average, and outputs a summary. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        )
    ]
    
    print("Running improved benchmarks...")
    results = runner.execute_suite(benchmarks)
    runner.export_results(results, "benchmark_results")
    print("Benchmarks completed. Results saved to benchmark_results/benchmark_results.md")

if __name__ == "__main__":
    main()
