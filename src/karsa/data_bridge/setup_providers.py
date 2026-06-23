"""Setup script to register data providers and LLM providers.

Run before starting the worker:
    uv run python -m karsa.data_bridge.setup_providers

Requires environment variables:
    DATA_BRIDGE_MASTER_KEY  — base64-encoded 32-byte AES key
    POLYGON_API_KEY         — Polygon.io API key
    FINNHUB_API_KEY         — Finnhub API key
    FMP_API_KEY             — Financial Modeling Prep API key (optional)
    ALPHA_VANTAGE_API_KEY   — Alpha Vantage API key (optional)
"""
import base64
import os
import sys

from psycopg_pool import ConnectionPool

from karsa.providers.application.credential_service import CredentialEncryptionService
from karsa.providers.application.data_bridge_services import DataBridgeProviderService
from karsa.providers.infrastructure.storage.data_bridge_repositories import (
    DataBridgeProviderRepository,
    ProviderHealthLogRepository,
)
from karsa.memory.infrastructure.event.postgres_event_bus import PostgresEventBus


def main():
    # Validate env vars
    master_key = os.environ.get("DATA_BRIDGE_MASTER_KEY")
    polygon_key = os.environ.get("POLYGON_API_KEY")
    finnhub_key = os.environ.get("FINNHUB_API_KEY")

    if not master_key:
        print("ERROR: DATA_BRIDGE_MASTER_KEY not set")
        print("Generate one: python3 -c \"import base64, os; print(base64.b64encode(os.urandom(32)).decode())\"")
        sys.exit(1)

    if not polygon_key:
        print("WARNING: POLYGON_API_KEY not set — skipping Polygon provider")

    if not finnhub_key:
        print("WARNING: FINNHUB_API_KEY not set — skipping Finnhub provider")

    # Connect to DB
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(dsn)
    session = Session(engine)

    pool = ConnectionPool(f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}", min_size=1, max_size=2)

    # Wire services
    event_bus = PostgresEventBus(pool)
    provider_repo = DataBridgeProviderRepository(session)
    health_repo = ProviderHealthLogRepository(session)
    credential_service = CredentialEncryptionService()
    service = DataBridgeProviderService(
        provider_repo=provider_repo,
        health_repo=health_repo,
        credential_service=credential_service,
        event_bus=event_bus,
    )

    # Register Polygon
    if polygon_key:
        existing = provider_repo.get_by_name("polygon")
        if existing:
            print(f"Polygon already registered (id={existing.provider_id})")
        else:
            provider = service.register_provider(
                name="polygon",
                ptype="market_tick",
                api_key=polygon_key,
                priority=10,
                initial_config={
                    "symbols": ["AAPL", "SPY", "TSLA", "MSFT", "GOOGL"],
                    "message_timeout_seconds": 60,
                    "tick_queue_size": 50000,
                },
            )
            print(f"✅ Registered Polygon (id={provider.provider_id})")

    # Register Finnhub
    if finnhub_key:
        existing = provider_repo.get_by_name("finnhub")
        if existing:
            print(f"Finnhub already registered (id={existing.provider_id})")
        else:
            provider = service.register_provider(
                name="finnhub",
                ptype="news",
                api_key=finnhub_key,
                priority=20,
                initial_config={
                    "category": "general",
                    "poll_interval_seconds": 60,
                    "health_cache_ttl_seconds": 300,
                },
            )
            print(f"✅ Registered Finnhub (id={provider.provider_id})")

    # IDX ticker universe (from MANDATE.md)
    IDX_TICKERS_YF = ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "ANTM.JK", "BMRI.JK", "ICBP.JK", "INDF.JK", "SMGR.JK", "MEDC.JK"]
    IDX_TICKERS_AV = ["BBCA", "BBRI", "TLKM", "ASII", "ANTM", "BMRI", "ICBP", "INDF", "SMGR", "MEDC"]

    # Register YFinance (no API key needed, primary EOD source)
    existing = provider_repo.get_by_name("yfinance")
    if existing:
        print(f"YFinance already registered (id={existing.provider_id})")
    else:
        provider = service.register_provider(
            name="yfinance",
            ptype="market_bar",
            api_key="",
            priority=10,
            initial_config={
                "tickers": IDX_TICKERS_YF,
                "schedule_hour_utc": 9,  # 16:00 WIB
            },
        )
        print(f"✅ Registered YFinance (id={provider.provider_id})")

    # Register FMP (secondary EOD + fundamentals)
    fmp_key = os.environ.get("FMP_API_KEY")
    if fmp_key:
        existing = provider_repo.get_by_name("fmp")
        if existing:
            print(f"FMP already registered (id={existing.provider_id})")
        else:
            provider = service.register_provider(
                name="fmp",
                ptype="market_bar",
                api_key=fmp_key,
                priority=20,
                initial_config={
                    "tickers": IDX_TICKERS_YF,
                    "poll_interval_seconds": 3600,
                },
            )
            print(f"✅ Registered FMP (id={provider.provider_id})")
    else:
        print("WARNING: FMP_API_KEY not set — skipping FMP provider")

    # Register Alpha Vantage (tertiary, rate-limited)
    av_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if av_key:
        existing = provider_repo.get_by_name("alpha_vantage")
        if existing:
            print(f"Alpha Vantage already registered (id={existing.provider_id})")
        else:
            provider = service.register_provider(
                name="alpha_vantage",
                ptype="market_bar",
                api_key=av_key,
                priority=30,
                initial_config={
                    "tickers": IDX_TICKERS_AV,
                    "poll_interval_seconds": 7200,
                    "per_ticker_delay_seconds": 3,
                },
            )
            print(f"✅ Registered Alpha Vantage (id={provider.provider_id})")
    else:
        print("WARNING: ALPHA_VANTAGE_API_KEY not set — skipping Alpha Vantage provider")

    # Register LLM providers (if llm_config_service available)
    try:
        from karsa.llm.infrastructure.storage.config_repository import LLMConfigRepository
        from karsa.llm.application.config_service import LLMConfigService

        llm_repo = LLMConfigRepository(conn)
        llm_service = LLMConfigService(
            config_repo=llm_repo,
            credential_service=credential_service,
            event_bus=event_bus,
        )

        # Register OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            existing = llm_repo.get_provider_by_name("openai")
            if not existing:
                llm_service.register_provider("openai", openai_key, "https://api.openai.com/v1", priority=10)
                llm_service.add_model_to_group("karsa-reasoning", "gpt-4o", "openai", priority=10, temperature=0.2)
                llm_service.add_model_to_group("karsa-fast", "gpt-4o-mini", "openai", priority=10, temperature=0.1)
                print("✅ Registered OpenAI LLM provider")
            else:
                print(f"OpenAI already registered (id={existing.provider_id})")

        # Register Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            existing = llm_repo.get_provider_by_name("anthropic")
            if not existing:
                llm_service.register_provider("anthropic", anthropic_key, "https://api.anthropic.com", priority=20)
                llm_service.add_model_to_group("karsa-reasoning", "claude-sonnet-4-6", "anthropic", priority=20, temperature=0.2)
                llm_service.add_model_to_group("karsa-fast", "claude-haiku-4-5-20251001", "anthropic", priority=20, temperature=0.1)
                print("✅ Registered Anthropic LLM provider")
            else:
                print(f"Anthropic already registered (id={existing.provider_id})")

        # Set router settings
        llm_service.update_router_settings("karsa-reasoning", num_retries=3, timeout_seconds=60)
        llm_service.update_router_settings("karsa-fast", num_retries=3, timeout_seconds=30)
        print("✅ LLM router settings configured")

    except Exception as e:
        print(f"LLM setup skipped: {e}")

    session.commit()
    session.close()
    pool.close()
    print("\n✅ Provider setup complete. Start worker with:")
    print("  uv run python -m karsa.data_bridge.worker")


if __name__ == "__main__":
    main()
