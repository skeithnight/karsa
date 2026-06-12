import pytest
from karsa.llm.prompts import build_pe_prompt, build_review_prompt

def test_pe_prompt_enforcements():
    objective = "Build a CLI"
    artifact = ""
    feedback = ""
    prompt = build_pe_prompt(objective, artifact, feedback)
    
    assert "README.md" in prompt
    assert "test_*.py" in prompt
    assert "Edge Case Coverage" in prompt
    assert "Multi-File Output" in prompt
    assert "<file path=" in prompt

def test_review_prompt_enforcements():
    objective = "Build a CLI"
    artifact = ""
    tool_output = "Exit code: 5"
    prompt = build_review_prompt(objective, artifact, tool_output)
    
    assert "Missing Tests" in prompt
    assert "test_*.py" in prompt
    assert "Exit code: 5" in prompt
    assert "README.md" in prompt
    assert "APPROVED only if" in prompt or "APPROVED if" in prompt or "ONLY output APPROVED" in prompt
