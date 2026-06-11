---
status: active
owner: Karsa Architecture Team
created: 2026-06-11
last_reviewed: 2026-06-11
next_review: 2026-09-11
---

# Documentation Quality Gate

Before any markdown file is merged into the repository, it must pass the following strict checklist. Failure to comply will result in an automatic rejection of the PR.

## Markdown Quality Checklist

- [ ] **Is it duplicating an existing document?** Check the `SSOT_MATRIX.md`. If the concept is already defined, do not create a new file.
- [ ] **Is an ADR more appropriate?** If you are documenting a technical choice, tradeoff, or structural pivot, use the ADR format in `docs/adr/` instead of a standalone architectural document.
- [ ] **Does a canonical document already exist?** Architecture changes must be patched into `01` through `05`. Do not create an `06` unless explicitly authorized by the Architecture Review Board.
- [ ] **Can an existing document be updated instead?** Prefer patching `ROADMAP.md` or `PROJECT_DASHBOARD.md` over creating a new status file.
- [ ] **Is lifecycle metadata present?** The YAML frontmatter block containing `status`, `owner`, `created`, `last_reviewed`, and `next_review` MUST be present at the top of the file.
