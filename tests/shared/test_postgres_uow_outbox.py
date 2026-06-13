import json
import pytest
from unittest.mock import MagicMock
import psycopg
from karsa.shared.infrastructure.postgres_uow import PostgresUnitOfWork
from karsa.shared.infrastructure.postgres_outbox import OutboxDispatcher
from karsa.shared.infrastructure.outbox import OutboxRecord
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = MagicMock()
    pool.getconn.return_value = conn
    pool.connection.return_value.__enter__.return_value = conn
    return pool

def test_uow_commit_and_outbox_dispatch(mock_pool):
    uow = PostgresUnitOfWork(mock_pool)
    conn = mock_pool.getconn.return_value
    cursor_mock = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor_mock
    
    with uow:
        payload_data = {"test": "data"}
        record = OutboxRecord(
            envelope_id="env-1",
            payload=json.dumps(payload_data),
            published_status=False
        )
        uow.outbox_repository.save(record)
        
    cursor_mock.execute.assert_called_with(
        "INSERT INTO outbox_records (envelope_id, payload, published_status) VALUES (%s, %s, %s)",
        ("env-1", '{"test": "data"}', False)
    )
    conn.commit.assert_called_once()
    mock_pool.putconn.assert_called_once_with(conn)

def test_uow_concurrency_conflict(mock_pool):
    uow = PostgresUnitOfWork(mock_pool)
    conn = mock_pool.getconn.return_value
    
    # Simulate Postgres SerializationFailure
    conn.commit.side_effect = psycopg.errors.SerializationFailure("Concurrent update")
    
    with pytest.raises(ConcurrencyConflictError, match="Transaction serialization failed"):
        with uow:
            pass
            
    conn.rollback.assert_called_once()

def test_outbox_dispatcher(mock_pool):
    dispatcher = OutboxDispatcher(mock_pool)
    conn = mock_pool.connection.return_value.__enter__.return_value
    cursor_mock = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor_mock
    
    # Mock finding pending records
    cursor_mock.fetchall.return_value = [
        ("env-1", '{"data": "1"}', 0),
        ("env-2", '{"data": "2"}', 3) # Exceeds retry limit for failing
    ]
    
    published = []
    def mock_publish(payload):
        if payload == '{"data": "2"}':
            raise Exception("Fail")
        published.append(payload)
        
    dispatched_count = dispatcher.dispatch_pending(mock_publish)
    
    assert dispatched_count == 1
    assert len(published) == 1
    assert published[0] == '{"data": "1"}'
    
    # Verify SQL calls
    assert "UPDATE outbox_records SET published_status = true WHERE envelope_id = ANY(%s)" in [call[0][0] for call in cursor_mock.execute.call_args_list]
    assert "UPDATE outbox_records SET dead_letter = true WHERE envelope_id = ANY(%s)" in [call[0][0] for call in cursor_mock.execute.call_args_list]
