import psycopg
from psycopg_pool import ConnectionPool
from karsa.shared.infrastructure.uow import UnitOfWork, ConcurrencyConflictError
from karsa.shared.infrastructure.postgres_outbox import PostgresOutboxRepository

class PostgresUnitOfWork(UnitOfWork):
    """
    Concrete UnitOfWork for PostgreSQL using psycopg.
    Provides transactional consistency and OCC handling.
    """
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.conn = None
        self.outbox_repository = None

    def start(self):
        """Begin a new transaction."""
        self.conn = self.pool.getconn()
        self.conn.autocommit = False
        self.outbox_repository = PostgresOutboxRepository(self.conn)

    def commit(self):
        """Commit the transaction. Catch database-level OCC or serialization conflicts."""
        if self.conn:
            try:
                self.conn.commit()
            except psycopg.errors.SerializationFailure:
                self.conn.rollback()
                raise ConcurrencyConflictError("Transaction serialization failed due to concurrent update.")
            except Exception:
                self.conn.rollback()
                raise
            finally:
                self.pool.putconn(self.conn)
                self.conn = None
                self.outbox_repository = None

    def rollback(self):
        """Rollback the transaction."""
        if self.conn:
            self.conn.rollback()
            self.pool.putconn(self.conn)
            self.conn = None
            self.outbox_repository = None
