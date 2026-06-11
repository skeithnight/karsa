# Documentation Governance Policy

1. No new architecture document may be created if the content belongs in an existing canonical architecture document.
2. Architecture decisions must be written as ADRs.
3. Sprint audits must be consolidated into a single audit package per sprint.
4. Sprint reports must be consolidated into a single report package per sprint.
5. Roadmap information exists only inside ROADMAP.md and PROJECT_STATUS.md.
6. Duplicate concepts across documents are prohibited.
7. Every new document must declare:
   - Owner
   - Purpose
   - Lifecycle
   - Review Frequency
8. Archive instead of deleting historical artifacts.
9. Maximum architecture document count:
   - Architecture: <= 10
   - ADRs: unlimited
   - Reviews: <= 5
   - Active reports: <= 10
10. Any future sprint that creates more than 5 new markdown files must justify why consolidation is not possible.
