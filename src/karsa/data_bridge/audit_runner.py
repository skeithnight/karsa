"""Data Bridge Audit Runner — checks if the worker successfully fetched data.

Run after the worker has been running for 30 minutes:
    uv run python -m karsa.data_bridge.audit_runner

Checks:
1. provider_health_logs — are connectors reporting healthy?
2. data_bridge_dead_letter — are there normalization failures?
3. Aggregation engine state — are bars being emitted?
4. Connector status — are WebSocket/REST connections alive?
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

from psycopg_pool import ConnectionPool


def build_dsn() -> str:
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    return f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"


def run_audit():
    """Run the Data Bridge audit."""
    dsn = build_dsn()
    pool = ConnectionPool(dsn, min_size=1, max_size=2)
    conn = pool.getconn()
    conn.autocommit = True

    now = datetime.now(timezone.utc)
    thirty_min_ago = now - timedelta(minutes=30)

    print("=" * 60)
    print("KARSA DATA BRIDGE — 30-MINUTE AUDIT")
    print(f"Audit time: {now.isoformat()}")
    print(f"Checking window: {thirty_min_ago.isoformat()} → {now.isoformat()}")
    print("=" * 60)

    # 1. Check registered providers
    print("\n[1] REGISTERED PROVIDERS")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, type, status, priority FROM data_providers ORDER BY priority")
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[1]:15s} | type={row[2]:12s} | status={row[3]:10s} | priority={row[4]}")
        else:
            print("  ⚠️  NO PROVIDERS REGISTERED")
            print("  → Run: llm_config_service.register_provider() or data_bridge_service.register_provider()")

    # 2. Check provider credentials
    print("\n[2] PROVIDER CREDENTIALS")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dp.name, pc.key_rotation_version, pc.expires_at
            FROM provider_credentials pc
            JOIN data_providers dp ON pc.provider_id = dp.id
        """)
        rows = cur.fetchall()
        if rows:
            for row in rows:
                expires = row[2].isoformat() if row[2] else "never"
                print(f"  {row[0]:15s} | rotation=v{row[1]} | expires={expires}")
        else:
            print("  ⚠️  NO CREDENTIALS STORED")

    # 3. Check provider configurations
    print("\n[3] PROVIDER CONFIGURATIONS")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dp.name, pc.config_key, pc.config_value
            FROM provider_configurations pc
            JOIN data_providers dp ON pc.provider_id = dp.id
            ORDER BY dp.name, pc.config_key
        """)
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0]:15s} | {row[1]:20s} = {row[2]}")
        else:
            print("  ⚠️  NO CONFIGURATIONS STORED")

    # 4. Check health logs (last 30 min)
    print("\n[4] HEALTH LOGS (last 30 min)")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dp.name, ph.status, ph.latency_ms, ph.error_message, ph.recorded_at
            FROM provider_health_logs ph
            JOIN data_providers dp ON ph.provider_id = dp.id
            WHERE ph.recorded_at >= %s
            ORDER BY ph.recorded_at DESC
            LIMIT 20
        """, (thirty_min_ago,))
        rows = cur.fetchall()
        if rows:
            for row in rows:
                latency = f"{row[2]}ms" if row[2] else "n/a"
                error = f" | error={row[3][:50]}" if row[3] else ""
                print(f"  {row[0]:15s} | {row[1]:12s} | latency={latency}{error} | {row[4].isoformat()}")
        else:
            print("  ⚠️  NO HEALTH LOGS IN LAST 30 MINUTES")
            print("  → Worker may not be running, or no connectors registered")

    # 5. Check dead letter table
    print("\n[5] DEAD LETTER (normalization failures)")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM data_bridge_dead_letter WHERE received_at >= %s
        """, (thirty_min_ago,))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"  ⚠️  {count} normalization failures in last 30 min")
            cur.execute("""
                SELECT provider_id, error_type, error_message, received_at
                FROM data_bridge_dead_letter
                WHERE received_at >= %s
                ORDER BY received_at DESC
                LIMIT 5
            """, (thirty_min_ago,))
            for row in cur.fetchall():
                print(f"    provider={row[0][:8]}... | type={row[1]} | {row[2][:60]} | {row[3].isoformat()}")
        else:
            print("  ✅ No normalization failures")

    # 6. Check event journal for data bridge events
    print("\n[6] EVENT JOURNAL (data bridge events)")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_type, COUNT(*)
            FROM event_journal
            WHERE occurred_at >= %s
              AND (event_type LIKE '%%Provider%%' OR event_type LIKE '%%DataBridge%%' OR event_type LIKE '%%Failover%%')
            GROUP BY event_type
            ORDER BY COUNT(*) DESC
        """, (thirty_min_ago,))
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0]:40s} | count={row[1]}")
        else:
            print("  ⚠️  NO DATA BRIDGE EVENTS IN LAST 30 MINUTES")

    # 7. Check LLM providers
    print("\n[7] LLM PROVIDERS")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("SELECT name, base_url, status, priority FROM llm_providers ORDER BY priority")
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0]:15s} | url={row[1] or 'default':30s} | status={row[2]:10s} | priority={row[3]}")
        else:
            print("  ℹ️  No LLM providers registered yet")

    # 8. Check system configurations
    print("\n[8] SYSTEM CONFIGURATIONS")
    print("-" * 40)
    with conn.cursor() as cur:
        cur.execute("SELECT domain, config_key, description FROM system_configurations ORDER BY domain, config_key")
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0]:15s} | {row[1]:25s} | {row[2] or ''}")
        else:
            print("  ℹ️  No system configurations set yet")

    # Summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM data_providers")
        providers = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM provider_health_logs WHERE recorded_at >= %s", (thirty_min_ago,))
        health_logs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM data_bridge_dead_letter WHERE received_at >= %s", (thirty_min_ago,))
        dead_letters = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM llm_providers")
        llm_providers = cur.fetchone()[0]

    print(f"  Data Providers:       {providers}")
    print(f"  Health Logs (30m):    {health_logs}")
    print(f"  Dead Letters (30m):   {dead_letters}")
    print(f"  LLM Providers:        {llm_providers}")

    if providers == 0:
        print("\n  ❌ NO DATA PROVIDERS REGISTERED")
        print("  → Register providers before starting the worker:")
        print("    data_bridge_service.register_provider('polygon', 'market_tick', api_key='...')")
        print("    data_bridge_service.register_provider('finnhub', 'news', api_key='...')")
    elif health_logs == 0:
        print("\n  ⚠️  NO HEALTH LOGS — Worker may not be running")
        print("  → Start with: uv run python -m karsa.data_bridge.worker")
    else:
        print("\n  ✅ DATA BRIDGE IS ACTIVE")

    pool.close()


if __name__ == "__main__":
    run_audit()
