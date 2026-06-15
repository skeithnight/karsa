# ADR-060: Governance Subject Polymorphism

## Context
The prior governance implementation strictly enforced policy limits uniquely upon `Worker` entities. The Virtual Investment Firm must ultimately control the risk vectors for `Strategy`, `Thesis`, `Capability`, and `Portfolio` entities based on objective historical performance, not just human agents.

## Decision
Introduce a polymorphic abstraction `GovernanceSubject` mapping evaluations against any of the 5 authorized vectors. The Governance Engine updates Trust Scores without explicit knowledge of the domain semantics of the Subject.

## Consequences
Scales governance capabilities across the entirety of the firm's architecture while preventing strict ownership leakage into Capital Allocation or Capability registries.
