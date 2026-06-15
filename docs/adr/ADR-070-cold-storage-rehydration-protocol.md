# ADR-070: Cold Storage Rehydration Protocol

## Status
Accepted

## Context
ADR-064 mandated S3/Parquet cold storage to resolve Postgres table bloat, but failed to specify how 10-year historical traces are restored into the execution environment for replay audits.

## Decision
We formalize a localized **Home Lab First Rehydration Lifecycle**:
1. **Export**: Day-8 telemetry is aggregated.
2. **Verify**: A cryptographic hash is calculated over the Parquet block to guarantee integrity.
3. **Archive**: Uploaded securely to a local NAS or MinIO instance (Home Lab first), with a cron-synced path to AWS S3 / Cloudflare R2 for off-site backup.
4. **Rehydrate**: A dedicated `RehydrationWorker` can be commanded to pull a specific date-range Parquet file from MinIO, read it via DuckDB (for low-memory analytic queries), or physically re-insert it into a dedicated `postgres_archive_sandbox` schema for full SQL relational replay.
5. **Safeguard**: Hot storage pruning is explicitly suspended if the Verification or Archival phases fail, prioritizing disk space alerts over silent data loss.

## Consequences
* Full 10-year audit replayability is guaranteed and operationally executable without cloud egress costs via the home lab NAS.
* Protects against silent S3 connectivity failures causing data loss.
