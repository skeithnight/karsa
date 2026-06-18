# ADR-095: Investment Intelligence Projection Ownership

- **Status**: Accepted
- **Date**: 2026-06-17
- **Supersedes**: N/A
- **Superseded By**: N/A

## Context
The UI required a `StockIntelligenceProjection` to aggregate data across seven disparate bounded contexts (Market Structure, Research, Forecast, Thesis, Decisions, Attribution, Risk). Initially, this projection was owned by the "Projection Worker". However, infrastructure cannot own business concepts. Additionally, restricting the projection strictly to "Stocks" limits future extensibility.

## Decision
We rename the projection to `InvestmentIntelligenceProjection` and formally assign its ownership to the **Read Model Platform**.

## Consequences
1. **Extensibility**: The identical schema pattern can now seamlessly serve Sector pages, Macro Theme pages, and Portfolio summary pages.
2. **Boundary Enforcement**: The Projection Worker is relegated purely to infrastructure (fetching events and executing SQL), while the Read Model Platform dictates the schema contract.
3. **CQRS Clarity**: Validates the complete isolation of UI read-models from core domain write-models.
