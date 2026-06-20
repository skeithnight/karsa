import pytest
from karsa.shared.domain.event import DomainEvent
from karsa.shared.domain.aggregate import AggregateRoot

from dataclasses import dataclass

@dataclass
class UserCreatedEvent(DomainEvent):
    username: str = ""

class UserAggregate(AggregateRoot):
    def __init__(self, user_id: str, username: str):
        super().__init__()
        self.aggregate_id = user_id
        self.username = username
        self.record_event(UserCreatedEvent(username=username))

def test_aggregate_records_events_and_increments_version():
    user = UserAggregate(user_id="u123", username="alice")
    
    events = user.pull_domain_events()
    assert len(events) == 1
    
    event = events[0]
    assert event.event_name == "UserCreatedEvent"
    assert getattr(event, "username") == "alice"
    assert user.version == 1

def test_stream_id_generation():
    user = UserAggregate(user_id="u456", username="bob")
    assert user.aggregate_id == "u456"
    assert user.aggregate_type == "UserAggregate"
    assert user.stream_id == "UserAggregate:u456"

def test_event_replay_metadata():
    user = UserAggregate(user_id="u999", username="charlie")
    events = user.pull_domain_events()
    ev = events[0]
    
    assert ev.event_id is not None
    assert ev.stream_id == "UserAggregate:u999"
    assert ev.aggregate_id == "u999"
    assert ev.aggregate_type == "UserAggregate"
    assert ev.schema_version == 1
    assert ev.occurred_at is not None

def test_stream_collision_prevention():
    # Because stream_id includes aggregate_type, two aggregates with same ID won't collide.
    class ProfileAggregate(AggregateRoot):
        def __init__(self, profile_id: str):
            super().__init__()
            self.aggregate_id = profile_id
            self.record_event(UserCreatedEvent(username="fake"))
    
    user = UserAggregate(user_id="shared-1", username="x")
    profile = ProfileAggregate(profile_id="shared-1")
    
    assert user.stream_id == "UserAggregate:shared-1"
    assert profile.stream_id == "ProfileAggregate:shared-1"
    assert user.stream_id != profile.stream_id
