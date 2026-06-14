# ADR-026: Trace Retention and Archival Architecture

## Status
Approved

## Date
2026-06-14

## Context
Tracing every LLM token count, FSM transition, and execution duration across hundreds of agents will generate gigabytes of telemetry data daily. Storing all detailed spans in hot databases indefinitely is financially unsustainable and degrades database read/write performance. We must design a tiered storage model that balances active developer debugging needs with long-term investment-firm compliance audits. We must also define capacity limits and sampling controls to handle trace explosion scalability.

## Decision
We implement a **Three-Tiered Trace Retention and Archival Architecture**:
1. **Tiered Storage Model**:
   - **Hot Tier (30 Days Retention)**:
     * Contains all detailed spans, annotations, and complete payloads (e.g. raw logs, errors, and metadata). Average span size is ~2.0 KB.
     * Stored in a high-performance database (PostgreSQL with timescaled partitioning or a dedicated column-oriented database) optimized for write throughput and developer queries.
   - **Warm Tier (1 Year Retention)**:
     * Contains execution metadata, cost references, and audit-level span skeletons. Average span size is ~200 Bytes.
     * Raw content payloads are completely stripped.
   - **Cold Tier (7 Years / Lifetime Retention)**:
     * Contains audit evidence records, governance decisions, and financial attribution summaries. Average span size is ~100 Bytes.
     * Exported to compressed, columnar **Parquet** files stored in cost-optimized Object Storage.
2. **Automated Partitioning and Pruning**:
   - The Hot database is partitioned daily or weekly based on span start times.
   - An asynchronous lifecycle worker runs daily to:
     * Compile warm summaries.
     * Export aging hot partitions to Parquet files in cold storage.
     * Drop expired hot database partitions to reclaim index and table space.
3. **Trace Scale & Capacity Planning**:
   We model capacity based on three growth tiers:
   - **100k Spans / Day**: Hot database size = **6.0 GB** (30 days); Warm database size = **7.3 GB** (1 year); Cold Parquet size = **25.5 GB** (7 years). Standard database instance capacity.
   - **1.0M Spans / Day**: Hot database size = **60.0 GB** (30 days); Warm database size = **73.0 GB** (1 year); Cold Parquet size = **255.5 GB** (7 years). High-performance partitioned database capacity.
   - **10M Spans / Day**: Hot database size = **600.0 GB** (30 days); Warm database size = **730.0 GB** (1 year); Cold Parquet size = **2,555.0 GB** (7 years). Distributed database nodes, partition strategies, write rate of 115.7 spans/second.
4. **Volume Control Strategy**:
   - **Cardinality Controls**: Restrict tag keys to static registry lists, preventing open-ended string identifiers from ballooning index sizes.
   - **Adaptive Sampling**: 10% sampling on successful internal spans, keeping 100% of errors, warnings, provider executions, and governance PDP check spans.

## Consequences
- **Constant Database Size**: Hot partition dropping keeps the active database compact, protecting query and insert speeds from degrading.
- **Storage Cost Optimization**: Columnar Parquet formats compress data heavily, reducing cold storage costs.
- **Auditable Compliance**: Permanent cold records are read-only and link directly to Karsa’s cryptographic governance chains.
- **Rehydration Overhead**: Accessing cold archival logs for historical debugging requires importing Parquet files back into active query engines, introducing search latency.
