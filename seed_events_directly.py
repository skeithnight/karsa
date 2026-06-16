import os
import uuid
import json
from datetime import datetime
import psycopg

def seed_events():
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = "localhost" # run on host
    db_port = "5432"
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    
    events = [
        {
            "event_id": str(uuid.uuid4()),
            "aggregate_id": "PORT-MAIN",
            "event_type": "PositionOpenedEvent",
            "payload": {
                "portfolio_id": "PORT-MAIN",
                "asset_id": "AAPL",
                "quantity": 100.0,
                "average_cost": 150.0
            },
            "occurred_at": datetime.utcnow().isoformat(),
            "correlation_id": str(uuid.uuid4()),
            "causation_id": str(uuid.uuid4())
        },
        {
            "event_id": str(uuid.uuid4()),
            "aggregate_id": "PORT-MAIN",
            "event_type": "PositionOpenedEvent",
            "payload": {
                "portfolio_id": "PORT-MAIN",
                "asset_id": "MSFT",
                "quantity": 200.0,
                "average_cost": 250.0
            },
            "occurred_at": datetime.utcnow().isoformat(),
            "correlation_id": str(uuid.uuid4()),
            "causation_id": str(uuid.uuid4())
        },
        {
            "event_id": str(uuid.uuid4()),
            "aggregate_id": "PORT-MAIN",
            "event_type": "PortfolioValuationCalculatedEvent",
            "payload": {
                "portfolio_id": "PORT-MAIN",
                "net_asset_value": 65000.0,
                "cash_balance": 10000.0,
                "positions": {
                    "AAPL": 15000.0,
                    "MSFT": 50000.0
                }
            },
            "occurred_at": datetime.utcnow().isoformat(),
            "correlation_id": str(uuid.uuid4()),
            "causation_id": str(uuid.uuid4())
        }
    ]
    
    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cur:
            for ev in events:
                cur.execute(
                    """
                    INSERT INTO event_journal 
                    (event_id, aggregate_id, event_type, payload, occurred_at, correlation_id, causation_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        ev["event_id"],
                        ev["aggregate_id"],
                        ev["event_type"],
                        json.dumps(ev["payload"]),
                        ev["occurred_at"],
                        ev["correlation_id"],
                        ev["causation_id"]
                    )
                )
        conn.commit()
    print("Inserted events successfully.")

if __name__ == "__main__":
    seed_events()
