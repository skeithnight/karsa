# Artifact Quality Audit

## 1. Root Cause Analysis

The root cause of the placeholder-level artifacts ("Revised Vision", "Revised Architecture", "No issues") is twofold:

1.  **MockLLMClient Hardcoded Returns**: In `src/karsa/llm/client.py`, the `MockLLMClient` was explicitly programmed to return static strings like `"# Vision\nRevised Vision\n---"` when the system prompt contained the word "REVISE". It was also programmed to return "None" for all review categories to bypass the revision loop quickly during tests. Because the CLI defaults to `MockLLMClient` if a `GEMINI_API_KEY` is not present, local executions default to generating these static strings instead of invoking a real LLM.
2.  **Weak Agent Prompts**: In `src/karsa/agents/product_engineer.py`, the original system prompts were too generic. For example, the vision prompt simply said: `"Draft a precise, short markdown VISION document based on the idea."` It lacked a rigid schema. When an LLM (even Gemini) receives this, it outputs arbitrary formats.

## 2. Evidence

**Evidence 1 (MockLLMClient Hardcoded Strings)**
File: `src/karsa/llm/client.py`
```python
        elif "REVISE" in sys_upper:
            return (
                "# Vision\nRevised Vision\n---\n"
                "# Architecture\nRevised Architecture\n---\n"
                "# Implementation Plan\nRevised Plan"
            )
```

**Evidence 2 (Weak Prompts)**
File: `src/karsa/agents/product_engineer.py`
```python
        vision_sys = (
            "You are a pragmatic CTO. Draft a precise, short markdown VISION document based on the idea. "
            "Focus on the core value proposition and ignore hypotheticals. Output only markdown."
        )
```
This prompt does not enforce the required sections: Problem, Goals, Non Goals, Success Criteria.

## 3. Recommended Fixes

1.  **Strict Schema Enforcement in Prompts**: Update `ProductEngineerAgent` to explicitly enforce the required Markdown headings:
    *   **Vision**: Must include Problem, Goals, Non Goals, Success Criteria.
    *   **Architecture**: Must include Architecture Overview, Components, Data Flow, Technology Decisions.
    *   **Implementation Plan**: Must include Phases, Tasks, Milestones.
2.  **Enhance ReviewAgent Prompt**: Make sure the ReviewAgent specifically checks for these sections and calls out their absence as a "Critical Issue."
3.  **Upgrade MockLLMClient**: While the Mock LLM shouldn't do real reasoning, it should return fully fleshed-out dummy documents that adhere to the new structural requirements, proving that the file writing and parsing logic handles complex markdown correctly.
