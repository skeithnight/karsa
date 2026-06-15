# Engineering Standards

## Purpose
This document defines the mandatory standards for code quality, security, version control, and release management in the Karsa repository. It complements the Documentation Style Guide and Workflow Rules.

## 1. Code & Version Control Governance
- **Commit Traceability**: All Git commit messages must reference the Sprint or ADR they belong to (e.g., `feat(auth): implement OAuth2 - refs ADR-005, sprint-02`).
- **PR Linkage**: Every Pull Request must explicitly link to the corresponding `docs/implementation/sprint-XX/plan.md` or `implementation.md` in its description.
- **Branch Protection**: The `main` branch is protected. Direct pushes are prohibited. All changes require a passing CI pipeline and at least one peer review approval.

## 2. Quality Assurance (QA) Thresholds
- **Definition of Done (DoD)**: A task is not complete until:
  - Unit test coverage does not drop below the repository baseline (e.g., 80%).
  - Zero critical or high-severity linting/static analysis errors exist.
- **Mandatory Testing**: Any ADR modifying the database schema or core API contracts requires evidence of a successful migration rollback test and contract test before merge.

## 3. Security & Compliance Governance
- **Zero-Tolerance Secrets Policy**: API keys, passwords, tokens, and private certificates must never be committed to the repository. Use environment variables or secret managers.
- **Data Governance**: No Personally Identifiable Information (PII) or production customer data may be used in test data, logs, or documentation.
- **Dependency Governance**: Introducing a new external library, framework, or SaaS tool requires an ADR to assess security, licensing, and maintenance risks.

## 4. Release & Deployment Governance
- **Versioning**: All releases must follow Semantic Versioning (SemVer: `MAJOR.MINOR.PATCH`).
- **Release Documentation**: Release notes must be generated in `docs/releases/vX.Y.Z.md` and explicitly reference the closed sprint's `implementation.md`.
- **Deployment Gates**: Deployment to production requires explicit sign-off in the PR or deployment ticket, confirming staging environment validation.

## 5. Incident & Emergency Management
- **Incident Workflow**: Production outages require the creation of an `INC-XXX.md` file in `docs/archive/` or a dedicated `docs/incidents/` folder.
- **Post-Mortem Integration**: All incident post-mortems must be summarized and linked into a sprint's `remediation.md` to ensure the root cause is permanently addressed.

## 6. Meta-Governance
- **Rule Evolution**: Changes to `DOCUMENTATION_STYLE_GUIDE.md`, `WORKFLOW_RULES.md`, or `ENGINEERING_STANDARDS.md` must be proposed via an ADR and require explicit approval from the Tech Lead or Architect.
- **Onboarding**: All new contributors must read and acknowledge these three governance documents before being granted write access to the repository.