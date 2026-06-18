# ADR-097: Research Findings to Thesis Contract

- **Status**: Accepted
- **Date**: 2026-06-17
- **Supersedes**: N/A
- **Superseded By**: N/A

## Context
The Research Engine and Thesis Engine boundaries were dangerously close to overlapping. If the Research Engine outputs "Conclusions" that resemble investment recommendations, the Thesis Engine risks becoming a meaningless rubber-stamp, violating the firm's strict hierarchy.

## Decision
We select **Option B**: Research strictly produces `Findings` and `Viewpoints`. Research is strictly prohibited from generating recommendations, target weights, or actionable execution parameters.

## Consequences
1. **Strict Hierarchy**: Research uncovers facts and synthesizes data (e.g., "Finding: BBCA CASA share is expanding due to XYZ"). The Thesis Engine formally declares the hypothesis and invalidation parameters based on those findings.
2. **Reusability**: A single Research artifact containing factual `Findings` can safely spawn multiple competing `ThesisVersions` (e.g., a Bull Thesis focusing on CASA expansion, and a Bear Thesis focusing on Valuation).
3. **Auditability**: Post-mortems trace failures precisely. If a trade fails, auditors can determine if the Research `Finding` was factually wrong, or if the Thesis `Hypothesis` simply misinterpreted accurate findings.
