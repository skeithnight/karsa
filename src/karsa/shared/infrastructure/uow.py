class ConcurrencyConflictError(Exception):
    """Raised when an optimistic concurrency check fails."""
    pass

class UnitOfWork:
    """Base interface for UnitOfWork."""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def commit(self):
        pass
    
    def rollback(self):
        pass
