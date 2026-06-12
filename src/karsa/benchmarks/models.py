from dataclasses import dataclass
from typing import List

@dataclass
class BenchmarkDefinition:
    benchmark_id: str
    benchmark_name: str
    objective: str
    expected_artifacts: List[str]
    success_criteria: List[str]

@dataclass
class BenchmarkResult:
    benchmark_id: str
    state: str
    review_cycles: int
    duration_seconds: float
    recovery_attempts: int
    generated_files: List[str]
    test_pass: bool
