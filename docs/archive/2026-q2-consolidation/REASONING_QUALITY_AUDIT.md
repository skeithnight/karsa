# Reasoning Quality Audit

## Root Cause Analysis

1.  **Overwriting Full Documents with Truncated Output**: In `ProductEngineerAgent.revise_design`, the LLM is instructed to rewrite all three artifacts (VISION, ARCHITECTURE, IMPLEMENTATION_PLAN) in a single response, separated by `---`. Because LLMs have output length limits and a tendency to summarize when generating multiple large documents simultaneously, the LLM truncates the reasoning and outputs trivial summaries (e.g., "Revised."). This overwrites the original, detailed artifacts with corrupted/summarized versions.
2.  **Lack of Deep Reasoning in Prompts**: While the previous audit enforced structure (headings), it did not enforce *reasoning depth*. The prompt simply asked for "Components" without demanding "Tradeoffs" or "Rationale." This led to superficial outputs.
3.  **MockLLMClient Artifact Corruption**: `MockLLMClient` explicitly returned `"Revised."` for the revised content, which physically overwrote the meaningful mock documents in the filesystem during local testing, reinforcing the appearance of an artifact corruption failure.

## Evidence

**Evidence 1: Artifact Overwrite Logic (Truncation)**
File: `src/karsa/agents/product_engineer.py`
```python
        parts = revised_content.split('---')
        if len(parts) >= 3:
            self.artifacts.write_artifact("docs/vision/VISION.md", parts[0].strip())
            # ... overwrites the entire file with potentially truncated content
```

**Evidence 2: Shallow Prompts**
File: `src/karsa/agents/product_engineer.py`
```python
        arch_sys = (
            "... You MUST include the following sections exactly: Architecture Overview, Components, Data Flow, Technology Decisions ..."
        )
```
*Issue: Misses crucial reasoning steps like Tradeoffs and Rationale.*

## Failure Scenarios

*   **Scenario A (The Summarization Trap)**: The LLM reads 1000 words of Vision, Architecture, and Implementation. It is asked to revise all three in one go based on a review. It outputs 300 words total, stripping out all the nuance, and `ArtifactManager` blindly overwrites the 1000-word originals with the 300-word summaries.
*   **Scenario B (Mock Corruption)**: The user runs the CLI locally without an API key. The `RevisionEngine` triggers. `MockLLMClient` returns `"Revised."` and the original detailed mock documents are destroyed.

## Recommended Fixes

1.  **Deep Reasoning Prompts**: Update `ProductEngineerAgent` to explicitly demand deep reasoning (e.g., "Target Users", "Rationale", "Tradeoffs", "Actionable tasks").
2.  **Anti-Summarization Directives**: Add explicit directives to the `revise_design` prompt: `"CRITICAL: Do NOT summarize. You MUST provide the FULL revised content for each document without losing any detail."`
3.  **Update MockLLMClient**: Replace the trivial `"Revised."` mock outputs with rich, multi-paragraph mock documents that explicitly contain the new required headings.
