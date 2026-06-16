import psycopg
from karsa.bootstrap import get_postgres_pool

def create():
    pool = get_postgres_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS decision_journals (
                    journal_ref TEXT PRIMARY KEY,
                    sealed_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS cio_decisions (
                    decision_id TEXT PRIMARY KEY,
                    calculation_id TEXT,
                    governance_exception_id TEXT,
                    decision_journal_ref TEXT UNIQUE NOT NULL,
                    portfolio_snapshot_hash TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_node_type TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    decision_payload JSONB NOT NULL,
                    cryptographic_signature TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portfolio_states (
                    state_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    portfolio_tree JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS post_mortem_records (
                    postmortem_id TEXT PRIMARY KEY,
                    incident_ref TEXT UNIQUE NOT NULL,
                    failure_classification JSONB NOT NULL,
                    root_causes JSONB NOT NULL,
                    findings JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS post_mortem_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    postmortem_id TEXT NOT NULL,
                    target_context TEXT NOT NULL,
                    action_item TEXT NOT NULL,
                    parameters JSONB NOT NULL,
                    state TEXT NOT NULL,
                    version INT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS recommendation_state_history (
                    history_id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    version INT NOT NULL,
                    transitioned_at TIMESTAMP NOT NULL
                );
            """)
        conn.commit()
    print("Tables created")

if __name__ == "__main__":
    create()
    pool = get_postgres_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS event_journal (
                    global_sequence BIGSERIAL PRIMARY KEY,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    aggregate_type TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    aggregate_version INT NOT NULL,
                    payload JSONB NOT NULL,
                    occurred_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projection_checkpoints (
                    projection_name TEXT PRIMARY KEY,
                    last_processed_sequence BIGINT NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'NOT_STARTED',
                    updated_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portfolio_read_valuations (
                    portfolio_id TEXT PRIMARY KEY,
                    net_asset_value FLOAT NOT NULL,
                    cash_balance FLOAT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portfolio_read_positions (
                    asset_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    quantity FLOAT NOT NULL,
                    average_cost FLOAT NOT NULL,
                    market_value FLOAT NOT NULL,
                    exposure_pct FLOAT NOT NULL,
                    exposure_value FLOAT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portfolio_read_cash_ledgers (
                    portfolio_id TEXT PRIMARY KEY,
                    balance FLOAT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
            """)
        conn.commit()
    print("ADR-071 Tables created")
