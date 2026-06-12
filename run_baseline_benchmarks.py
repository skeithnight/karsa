import os
import sys
from karsa.llm.client import GeminiClient
from karsa.llm.provider import ProviderManager
from karsa.llm.pool import ProviderPool
from karsa.benchmarks.models import BenchmarkDefinition
from karsa.benchmarks.runner import BenchmarkSuiteRunner

class MockBaselineProvider:
    def __init__(self):
        self.calls = {}
        
    def generate(self, prompt: str) -> str:
        # Simulate the known baseline failures of Karsa before prompt tuning:
        # 1. PE hallucinates or forgets tests.
        # 2. Review Agent approves too easily or loops.
        if "Product Engineer" in prompt:
            return """<file path="main.py">
def do_work(): pass
</file>"""
        elif "Review Agent" in prompt:
            # Simulate infinite loop or false approval
            return '{"decision": "REVISE", "convergence_score": 0.5, "blocking_issues": ["No test found"]}'

def main():
    provider_manager = MockBaselineProvider()
    runner = BenchmarkSuiteRunner(provider_manager)
    
    benchmarks = [
        BenchmarkDefinition(
            benchmark_id="bm_001_duplicate_finder",
            benchmark_name="Duplicate File Finder CLI",
            objective="Build a Python CLI duplicate file finder that uses SHA-256 to find duplicates in a directory. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_002_expense_tracker",
            benchmark_name="Expense Tracker CLI",
            objective="Build a Python Expense Tracker CLI using sqlite3 to add, list, and summarize expenses. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_003_todo_api",
            benchmark_name="Todo REST API",
            objective="Build a Python Todo REST API using the http.server standard library (do not use Flask/FastAPI). Include memory persistence and full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_004_static_site",
            benchmark_name="Markdown Static Site Generator",
            objective="Build a Python tool to convert a folder of .md files into .html files. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        ),
        BenchmarkDefinition(
            benchmark_id="bm_005_csv_analysis",
            benchmark_name="CSV Data Analysis Utility",
            objective="Build a Python CSV Data Analysis Utility that reads a dataset, calculates min/max/average, and outputs a summary. Include full pytest coverage.",
            expected_artifacts=[],
            success_criteria=[]
        )
    ]
    
    print("Running baseline benchmarks...")
    results = runner.execute_suite(benchmarks)
    runner.export_results(results, "benchmark_results")
    print("Benchmarks completed. Results saved to benchmark_results/benchmark_results.md")

if __name__ == "__main__":
    main()
