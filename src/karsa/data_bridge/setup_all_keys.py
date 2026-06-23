"""Setup all API keys in PostgreSQL.

Generates master key, encrypts all API keys, and registers
data providers + LLM providers in the database.

Usage:
    uv run python -m karsa.data_bridge.setup_all_keys
"""
import base64
import json
import os
import sys
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def main():
    # --- 1. Master Key ---
    master_key_b64 = os.environ.get("DATA_BRIDGE_MASTER_KEY")
    if not master_key_b64:
        master_key = os.urandom(32)
        master_key_b64 = base64.b64encode(master_key).decode("ascii")
        print(f"Generated DATA_BRIDGE_MASTER_KEY: {master_key_b64}")
        print("SAVE THIS KEY — you cannot decrypt credentials without it!")
    else:
        master_key = base64.b64decode(master_key_b64)
        print(f"Using existing DATA_BRIDGE_MASTER_KEY")

    aesgcm = AESGCM(master_key)

    def encrypt(plaintext: str) -> tuple[str, str]:
        """Returns (ciphertext_b64, nonce_b64)."""
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(ct).decode("ascii"), base64.b64encode(nonce).decode("ascii")

    # --- 2. Database Connection ---
    import psycopg

    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")

    conninfo = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_pass}"
    conn = psycopg.connect(conninfo, autocommit=True)
    cur = conn.cursor()

    # --- 3. API Keys (from env vars or prompt) ---
    api_keys = {
        "polygon": {
            "type": "market_tick",
            "priority": 10,
            "key": os.environ.get("POLYGON_API_KEY", ""),
            "config": {
                "symbols": ["AAPL", "SPY", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA"],
                "message_timeout_seconds": 60,
                "tick_queue_size": 50000,
            },
        },
        "finnhub": {
            "type": "news",
            "priority": 20,
            "key": os.environ.get("FINNHUB_API_KEY", ""),
            "config": {
                "category": "general",
                "poll_interval_seconds": 60,
                "health_cache_ttl_seconds": 300,
            },
        },
    }

    # LLM providers
    llm_keys = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "priority": 10,
            "key": os.environ.get("OPENAI_API_KEY", ""),
            "models": {
                "karsa-reasoning": [("gpt-4o", 10, 0.2)],
                "karsa-fast": [("gpt-4o-mini", 10, 0.1)],
            },
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com",
            "priority": 20,
            "key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "models": {
                "karsa-reasoning": [("claude-sonnet-4-6", 20, 0.2)],
                "karsa-fast": [("claude-haiku-4-5-20251001", 20, 0.1)],
            },
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com",
            "priority": 30,
            "key": os.environ.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY_1", "")),
            "models": {
                "karsa-reasoning": [("gemini-2.5-pro", 30, 0.2)],
                "karsa-fast": [("gemini-2.5-flash", 30, 0.1)],
            },
        },
        "mimo": {
            "base_url": os.environ.get("MIMO_BASE_URL", "https://api.mimo.ai"),
            "priority": 40,
            "key": os.environ.get("MIMO_API_KEY", ""),
            "models": {
                "karsa-reasoning": [("mimo-v2.5-pro", 40, 0.2)],
                "karsa-fast": [("mimo-v2.5-fast", 40, 0.1)],
            },
        },
    }

    # --- 4. Register Data Providers ---
    print("\n[DATA PROVIDERS]")
    print("-" * 50)

    for name, cfg in api_keys.items():
        api_key = cfg["key"]
        if not api_key:
            print(f"  ⚠️  {name}: No API key set (set {name.upper()}_API_KEY env var)")
            continue

        # Check if exists
        cur.execute("SELECT id FROM data_providers WHERE name = %s", (name,))
        row = cur.fetchone()
        if row:
            provider_id = str(row[0])
            print(f"  ℹ️  {name}: Already registered (id={provider_id})")
        else:
            provider_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO data_providers (id, name, type, status, priority) VALUES (%s, %s, %s, 'active', %s)",
                (provider_id, name, cfg["type"], cfg["priority"]),
            )
            print(f"  ✅ {name}: Registered (id={provider_id}, type={cfg['type']})")

        # Encrypt and store credential
        ct, nonce = encrypt(api_key)
        cur.execute("""
            INSERT INTO provider_credentials (provider_id, api_key_encrypted, api_key_nonce, key_rotation_version)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (provider_id) DO UPDATE SET
                api_key_encrypted = EXCLUDED.api_key_encrypted,
                api_key_nonce = EXCLUDED.api_key_nonce,
                key_rotation_version = provider_credentials.key_rotation_version + 1
        """, (provider_id, ct, nonce))
        print(f"       Credentials encrypted and stored")

        # Store config
        for key, value in cfg["config"].items():
            cur.execute("""
                INSERT INTO provider_configurations (id, provider_id, config_key, config_value)
                VALUES (gen_random_uuid(), %s, %s, %s::jsonb)
                ON CONFLICT (provider_id, config_key) DO UPDATE SET config_value = EXCLUDED.config_value
            """, (provider_id, key, json.dumps(value)))
        print(f"       Config: {list(cfg['config'].keys())}")

    # --- 5. Register LLM Providers ---
    print("\n[LLM PROVIDERS]")
    print("-" * 50)

    for name, cfg in llm_keys.items():
        api_key = cfg["key"]
        if not api_key:
            print(f"  ⚠️  {name}: No API key set (set {name.upper()}_API_KEY env var)")
            continue

        # Check if exists
        cur.execute("SELECT id FROM llm_providers WHERE name = %s", (name,))
        row = cur.fetchone()
        if row:
            provider_id = str(row[0])
            print(f"  ℹ️  {name}: Already registered (id={provider_id})")
        else:
            provider_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO llm_providers (id, name, base_url, status, priority) VALUES (%s, %s, %s, 'active', %s)",
                (provider_id, name, cfg["base_url"], cfg["priority"]),
            )
            print(f"  ✅ {name}: Registered (id={provider_id}, url={cfg['base_url']})")

        # Encrypt and store credential
        ct, nonce = encrypt(api_key)
        cur.execute("""
            INSERT INTO llm_provider_credentials (provider_id, api_key_encrypted, api_key_nonce, key_rotation_version)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (provider_id) DO UPDATE SET
                api_key_encrypted = EXCLUDED.api_key_encrypted,
                api_key_nonce = EXCLUDED.api_key_nonce,
                key_rotation_version = llm_provider_credentials.key_rotation_version + 1
        """, (provider_id, ct, nonce))
        print(f"       Credentials encrypted and stored")

        # Register model groups
        for group_name, models in cfg["models"].items():
            for model_name, priority, temperature in models:
                cur.execute("""
                    INSERT INTO llm_model_groups (id, group_name, model_name, provider_id, priority, temperature, is_active)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, true)
                    ON CONFLICT (group_name, model_name, provider_id) DO NOTHING
                """, (group_name, model_name, provider_id, priority, temperature))
                print(f"       Model: {group_name} → {model_name} (priority={priority})")

    # --- 6. Router Settings ---
    print("\n[LLM ROUTER SETTINGS]")
    print("-" * 50)

    for group_name in ["karsa-reasoning", "karsa-fast"]:
        timeout = 60 if group_name == "karsa-reasoning" else 30
        cur.execute("""
            INSERT INTO llm_router_settings (group_name, routing_strategy, num_retries, timeout_seconds, allowed_fails)
            VALUES (%s, 'latency-based-routing', 3, %s, 2)
            ON CONFLICT (group_name) DO UPDATE SET timeout_seconds = EXCLUDED.timeout_seconds
        """, (group_name, timeout))
        print(f"  ✅ {group_name}: retries=3, timeout={timeout}s, allowed_fails=2")

    # --- 7. System Config ---
    print("\n[SYSTEM CONFIGURATIONS]")
    print("-" * 50)

    system_configs = [
        ("risk", "max_position_pct", 0.05, "Max position as % of portfolio"),
        ("risk", "max_daily_turnover_usd", 5000000, "Daily turnover circuit breaker"),
        ("risk", "max_single_order_usd", 500000, "Max single order value"),
        ("execution", "default_order_type", "LIMIT", "Default order type for execution"),
        ("execution", "paper_trading", True, "Paper trading mode"),
        ("alerts", "stale_data_timeout_seconds", 300, "Stale data circuit breaker timeout"),
    ]

    for domain, key, value, desc in system_configs:
        cur.execute("""
            INSERT INTO system_configurations (domain, config_key, config_value, description)
            VALUES (%s, %s, %s::jsonb, %s)
            ON CONFLICT (domain, config_key) DO UPDATE SET config_value = EXCLUDED.config_value
        """, (domain, key, json.dumps(value), desc))
        print(f"  ✅ {domain}.{key} = {json.dumps(value)}")

    # --- 8. Summary ---
    print("\n" + "=" * 50)
    print("SETUP COMPLETE")
    print("=" * 50)

    cur.execute("SELECT COUNT(*) FROM data_providers")
    dp_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM llm_providers")
    llm_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM system_configurations")
    sc_count = cur.fetchone()[0]

    print(f"  Data Providers:  {dp_count}")
    print(f"  LLM Providers:   {llm_count}")
    print(f"  System Configs:  {sc_count}")
    print(f"\n  Master Key: {master_key_b64}")
    print(f"\n  Save this to .env:")
    print(f"  DATA_BRIDGE_MASTER_KEY={master_key_b64}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
