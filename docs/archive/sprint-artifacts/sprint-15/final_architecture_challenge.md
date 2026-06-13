# Sprint-15 Final Architecture Challenge - Daily Bucket Necessity Review

## 1. Executive Summary
This Final Architecture Challenge rigorously evaluates the structural necessity of the `DailyPnlBucket` projection layer. By mathematically modeling the query escalation costs of calculating multi-month rolling windows on high-frequency algorithmic trade data, this review proves that bypassing buckets leads to catastrophic read amplification (billions of row scans per day per worker). The review explicitly confirms that the Daily Bucket is a mathematically pure, indispensable optimization projection, resolving all lingering architectural hesitation.

## 2. Daily Bucket Justification (Necessity Analysis)
- **Why does it exist?** To act as a mathematical focal point. A 90-day rolling window must sum 90 discrete days. Without a daily bucket, it must sum the raw `DecisionPerformanceRecord`s for those 90 days. 
- **What problem does it solve?** It compresses O(N * D) window summations into O(D), where N is trades-per-day and D is the window length.
- **What breaks if removed?** The database CPU will rapidly saturate under high-volume workloads due to exponential read amplification during window materialization.

## 3. Complexity Analysis
- **Option A (Decision -> Bucket -> Window)**:
  - Write Amplification: Medium (1 bucket upsert, 1 window upsert per event).
  - Read Amplification: Low (Reads only today's decisions for bucket recompute, plus 90 bucket rows for the window).
  - Replay Cost: Medium.
- **Option B (Decision -> Window directly)**:
  - Write Amplification: Low (1 window upsert per event).
  - Read Amplification: Extreme. To recompute a 90-day window idempotently, the DB must `SUM()` all decisions over the last 90 days on *every single event*.
  - Replay Cost: Severe.

## 4. Recomputation Cost Proof (Challenge Area 3)
*Cost of updating the "Recompute Bucket" on every trade, summed over the course of a single day:*
- **10 trades/day**: `(10 * 11) / 2` = **55** total rows scanned per day.
- **100 trades/day**: `(100 * 101) / 2` = **5,050** total rows scanned per day.
- **1,000 trades/day**: `(1000 * 1001) / 2` = **500,500** total rows scanned per day.
- **10,000 trades/day**: `(10000 * 10001) / 2` = **50,005,000** total rows scanned per day.

*Cost of Option B (No Buckets) updating a 90-day window directly on every trade:*
- **10,000 trades/day**: The 90-day window contains ~900,000 historical trades. Summing 900,000 rows on every new trade (10,000 times) = **9,000,000,000** (9 Billion) rows scanned per day, *for a single worker*.

**Conclusion**: The 50 million read cost of the Recompute Bucket is trivially handled by a PostgreSQL Index-Only Scan. The 9 Billion read cost of skipping the bucket will trigger severe CPU exhaustion. 

## 5. Window Materialization Alternatives
1. **Daily Bucket (Recomputed)**: Fully idempotent, easily replayed, completely scalable, low operational complexity.
2. **Incremental Window Projection**: O(1) mathematical additions (`new_window = old_window - day_91_pnl + today_pnl`). Highly susceptible to race conditions and duplicate delivery bugs (non-idempotent).
3. **Hybrid Model**: Batch computation via cron jobs. Violates near-real-time streaming CQRS intent.

## 6. Architecture Purity Analysis
The `DailyPnlBucket` is unequivocally an **optimization projection**. 
- It contains zero independent truth.
- It can be dropped and deterministically recreated from `projection_decision_performance`.
- It exists solely to mathematically protect the database from query amplification during the materialization of `PerformanceWindowProfile`.
It perfectly respects the zero-aggregate, Projection-Only Authority of Architecture Revision v6.

## 7. Recommendation
**KEEP_DAILY_BUCKETS_AS_OPTIMIZATION_LAYER**

**Justification**: The O(N) daily recomputation cost of maintaining the bucket is magnitudes safer and cheaper than the O(N * D) continuous cost of bypassing it. The bucket is architecturally pure, highly performant, and structurally necessary for high-frequency trading capabilities. No changes to the Sprint-15 architecture or implementation plan are required.
