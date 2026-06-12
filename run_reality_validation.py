import os
import sys
from pathlib import Path

def main():
    from karsa.llm.client import GeminiClient
    from karsa.llm.provider import ProviderManager
    from karsa.llm.pool import ProviderPool
    from karsa.benchmarks.models import BenchmarkDefinition
    from karsa.benchmarks.runner import BenchmarkSuiteRunner

    pool = ProviderPool("gemini", [], Path(".karsa/providers.json"))
    gemini_client = GeminiClient(obs_manager=None, pool=pool)
    provider_manager = ProviderManager(providers=[gemini_client])
    
    runner = BenchmarkSuiteRunner(provider_manager)
    
    benchmark = BenchmarkDefinition(
        benchmark_id="bm_reality_check",
        benchmark_name="Reality Certification",
        objective="Create a Python function add(a, b) and a pytest validating add(2,3)==5",
        expected_artifacts=[],
        success_criteria=[]
    )
    
    print("Running reality validation using real provider...")
    results = runner.execute_suite([benchmark])
    
    print(results)

if __name__ == "__main__":
    main()
