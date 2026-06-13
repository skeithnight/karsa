class ConcurrencyConflictError(Exception):
    """Raised when an optimistic concurrency control conflict is detected."""
    pass

class UnitOfWork:
    """
    Abstract Unit of Work ensuring single-aggregate mutations 
    with transactional consistency and outbox staging.
    """
    def __enter__(self) -> 'UnitOfWork':
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

    def start(self):
        """Begin the transaction."""
        raise NotImplementedError

    def commit(self):
        """Commit the transaction. Validates single-aggregate rule if possible."""
        raise NotImplementedError

    def rollback(self):
        """Rollback the transaction."""
        raise NotImplementedError
