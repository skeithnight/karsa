"""sprint54 llm pool config schema + system configurations

Revision ID: 108
Revises: 107
Create Date: 2026-06-22

"""
from alembic import op

revision = '108'
down_revision = '107'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. LLM Providers (OpenAI, Anthropic, Mistral)
    op.execute("""
    CREATE TABLE llm_providers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(50) UNIQUE NOT NULL,
        base_url VARCHAR(255),
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'maintenance')),
        priority INT DEFAULT 100,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    # 2. Encrypted API Keys for LLM Providers
    op.execute("""
    CREATE TABLE llm_provider_credentials (
        provider_id UUID PRIMARY KEY REFERENCES llm_providers(id) ON DELETE CASCADE,
        api_key_encrypted TEXT NOT NULL,
        api_key_nonce TEXT NOT NULL DEFAULT '',
        api_secret_encrypted TEXT,
        api_secret_nonce TEXT,
        key_rotation_version INT DEFAULT 1,
        expires_at TIMESTAMPTZ
    );
    """)

    # 3. Model Groups (karsa-reasoning, karsa-fast)
    op.execute("""
    CREATE TABLE llm_model_groups (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        group_name VARCHAR(50) NOT NULL,
        model_name VARCHAR(100) NOT NULL,
        provider_id UUID REFERENCES llm_providers(id) ON DELETE CASCADE,
        priority INT DEFAULT 100,
        temperature FLOAT DEFAULT 0.2,
        max_tokens INT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(group_name, model_name, provider_id)
    );
    """)

    # 4. Router Settings (per group)
    op.execute("""
    CREATE TABLE llm_router_settings (
        group_name VARCHAR(50) PRIMARY KEY,
        routing_strategy VARCHAR(30) DEFAULT 'latency-based-routing',
        num_retries INT DEFAULT 3,
        timeout_seconds INT DEFAULT 60,
        allowed_fails INT DEFAULT 2,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    # 5. System Configurations (generic cross-cutting config)
    op.execute("""
    CREATE TABLE system_configurations (
        domain VARCHAR(50) NOT NULL,
        config_key VARCHAR(100) NOT NULL,
        config_value JSONB NOT NULL,
        description TEXT,
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (domain, config_key)
    );
    """)

    # Indexes
    op.execute("CREATE INDEX idx_llm_model_groups_group ON llm_model_groups (group_name);")
    op.execute("CREATE INDEX idx_llm_model_groups_provider ON llm_model_groups (provider_id);")
    op.execute("CREATE INDEX idx_system_config_domain ON system_configurations (domain);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS system_configurations;")
    op.execute("DROP TABLE IF EXISTS llm_router_settings;")
    op.execute("DROP TABLE IF EXISTS llm_model_groups;")
    op.execute("DROP TABLE IF EXISTS llm_provider_credentials;")
    op.execute("DROP TABLE IF EXISTS llm_providers;")
