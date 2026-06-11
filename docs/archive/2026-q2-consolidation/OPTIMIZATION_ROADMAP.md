# Post-Observability Optimization Roadmap

## Overview
Once the Cost & Token Observability Foundation is fully implemented, the platform will have hard data on where the majority of token consumption occurs. Based on historical multi-agent execution patterns, we anticipate large context windows during iterative review cycles to be the primary cost driver. 

The following roadmap identifies the highest ROI cost-reduction opportunities to pursue next.

## 1. Patch-Based Revisions
- **Concept**: Instead of rewriting the entire source file during a codebase change, the Coder agent generates diffs or standard patch formats.
- **Expected Savings**: High (70%+ reduction in output tokens per file edit).
- **Complexity**: High (Requires deterministic diff application and strict format adherence).
- **Risk**: Moderate (Diff application failures can halt workflows).
- **Implementation Priority**: P0

## 2. Review Delta Strategy
- **Concept**: The Reviewer agent currently re-evaluates the entire context upon every revision. Shift to evaluating only the delta (the diff applied) against the specific isolated review comments.
- **Expected Savings**: Very High (Massive reduction in Reviewer input tokens on subsequent cycles).
- **Complexity**: High (Requires semantic mapping of diffs to existing review threads).
- **Risk**: High (Risk of missing cascading side-effects outside the diff).
- **Implementation Priority**: P1

## 3. Context Compression
- **Concept**: Strip unnecessary whitespace, remove unrelated log artifacts, and dynamically minify code sent to the LLM.
- **Expected Savings**: Moderate (10-20% input token reduction).
- **Complexity**: Low.
- **Risk**: Low (As long as minification doesn't destroy syntax significance like in Python).
- **Implementation Priority**: P1

## 4. Prompt Summarization (Rolling History)
- **Concept**: For long-running agents or interactive sessions, summarize previous turns into a dense paragraph rather than passing the exact chat history.
- **Expected Savings**: High (Prevents unbounded input token growth).
- **Complexity**: Moderate (Requires a lightweight, cheap model to perform the summarization).
- **Risk**: Moderate (Potential loss of nuanced historical context).
- **Implementation Priority**: P2

## 5. Model Routing
- **Concept**: Dynamically route tasks to cheaper models based on complexity. E.g., use a cheap, fast model for syntax checking, and a premier model for deep architectural design.
- **Expected Savings**: Very High (Up to 90% cost reduction on simple tasks).
- **Complexity**: High (Requires an intelligent router and standardized prompt formats across different providers).
- **Risk**: Moderate (Cheaper models may hallucinate or fail tasks they were assumed capable of).
- **Implementation Priority**: P2

## 6. Artifact Diff Reviews
- **Concept**: Generate localized patches for Markdown artifacts instead of replacing entire structural documents. 
- **Expected Savings**: Moderate (Reduces output tokens on architecture documents).
- **Complexity**: Low (Text diffs are easier to apply than code AST changes).
- **Risk**: Low.
- **Implementation Priority**: P3

## 7. Semantic Retrieval / RAG (Knowledge Reuse)
- **Concept**: Instead of injecting the entire project design into the system prompt for every execution, index the context and retrieve only the chunks relevant to the specific agent's immediate task.
- **Expected Savings**: High (Massive reduction in base system prompt size).
- **Complexity**: Very High (Requires vector databases or local embedding indexing).
- **Risk**: Moderate (Poor retrieval leads to agents missing critical context, breaking the build).
- **Implementation Priority**: P3
