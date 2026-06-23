"""sprint51 data bridge provider schema

Revision ID: 105
Revises: 104
Create Date: 2026-06-22

"""
from alembic import op

revision = '105'
down_revision = '104'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Provider Registry
    op.execute("""
    CREATE TABLE data_providers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(50) UNIQUE NOT NULL,
        type VARCHAR(20) NOT NULL CHECK (type IN ('market_tick', 'market_bar', 'news', 'sentiment')),
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'maintenance')),
        priority INT DEFAULT 100,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    # 2. Encrypted Credentials
    op.execute("""
    CREATE TABLE provider_credentials (
        provider_id UUID PRIMARY KEY REFERENCES data_providers(id) ON DELETE CASCADE,
        api_key_encrypted TEXT NOT NULL,
        api_secret_encrypted TEXT,
        key_rotation_version INT DEFAULT 1,
        expires_at TIMESTAMPTZ
    );
    """)

    # 3. Dynamic Configuration (JSONB)
    op.execute("""
    CREATE TABLE provider_configurations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        provider_id UUID REFERENCES data_providers(id) ON DELETE CASCADE,
        config_key VARCHAR(100) NOT NULL,
        config_value JSONB NOT NULL,
        UNIQUE(provider_id, config_key)
    );
    """)

    # 4. Health & Uptime Tracking
    op.execute("""
    CREATE TABLE provider_health_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        provider_id UUID REFERENCES data_providers(id),
        status VARCHAR(20) CHECK (status IN ('connected', 'disconnected', 'rate_limited', 'auth_error')),
        error_message TEXT,
        latency_ms INT,
        recorded_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    # 5. pg_notify trigger for hot-reload
    op.execute("""
    CREATE OR REPLACE FUNCTION notify_provider_config_change() RETURNS TRIGGER AS $$
    BEGIN
      PERFORM pg_notify('provider_config_updated', NEW.provider_id::TEXT);
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER config_change_trigger
    AFTER INSERT OR UPDATE ON provider_configurations
    FOR EACH ROW EXECUTE FUNCTION notify_provider_config_change();
    """)

    # 6. Index for fast health log queries
    op.execute("""
    CREATE INDEX idx_provider_health_logs_lookup
    ON provider_health_logs (provider_id, recorded_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS config_change_trigger ON provider_configurations;")
    op.execute("DROP FUNCTION IF EXISTS notify_provider_config_change();")
    op.execute("DROP TABLE IF EXISTS provider_health_logs;")
    op.execute("DROP TABLE IF EXISTS provider_configurations;")
    op.execute("DROP TABLE IF EXISTS provider_credentials;")
    op.execute("DROP TABLE IF EXISTS data_providers;")
