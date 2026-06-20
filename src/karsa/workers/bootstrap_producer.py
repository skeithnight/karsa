import os
import uuid
from datetime import datetime, timezone
from karsa.bootstrap import ApplicationContainer
from karsa.domain.events import DomainEvent
from karsa.shared.infrastructure.event_journal import EventJournalRepository

class OrderFilledEvent(DomainEvent):
    def __init__(self, portfolio_id: str, asset_id: str, units: str, price: str):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Portfolio-{portfolio_id}"
        self.aggregate_id = portfolio_id
        self.aggregate_type = "Portfolio"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        
        self.portfolio_id = portfolio_id
        self.asset_id = asset_id
        self.units = units
        self.price = price
        self.timestamp = self.occurred_at.isoformat()
        self.correlation_id = str(uuid.uuid4())
        self.causation_id = str(uuid.uuid4())
        self.commission_bps = "0.0"
        self.fill_id = str(uuid.uuid4())

    def to_dict(self):
        return {
            "portfolio_id": self.portfolio_id,
            "asset_id": self.asset_id,
            "units": self.units,
            "price": self.price,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "commission_bps": self.commission_bps,
            "fill_id": self.fill_id,
            "event_id": self.event_id
        }

def run_bootstrap():
    print("Starting bootstrap producer...")
    
    # Initialize application container which connects to Postgres
    container = ApplicationContainer()
    try:
        event = OrderFilledEvent(
            portfolio_id="MAIN",
            asset_id="SPY",
            units="100.0",
            price="500.0"
        )
        
        with container.pool.connection() as conn:
            repo = EventJournalRepository(conn)
            # get current stream version
            current_version = repo.get_current_stream_version(event.stream_id)
            repo.append(event, current_version + 1)
            conn.commit()
            
        print(f"Successfully published OrderFilledEvent for portfolio MAIN")
        print(f"Payload: {event.to_dict()}")
    except Exception as e:
        print(f"Bootstrap producer failed: {e}")
        raise e
    finally:
        container.close()
        
    print("Bootstrap producer completed. Exiting 0.")

if __name__ == "__main__":
    run_bootstrap()
