import pytest
from datetime import datetime, timedelta
from karsa.providers.domain.models import ProviderDefinition, ProviderHealth, DatalakeBlob
from karsa.providers.application.services import ProviderRegistryService, ProviderHealthService, DatalakeService
from karsa.providers.domain.client import ProviderClient

class DummyClient(ProviderClient):
    def fetch_asset(self, asset_id):
        super().fetch_asset(asset_id)
    def fetch_universe(self, uid):
        super().fetch_universe(uid)
    def health_check(self):
        super().health_check()

class DummyUoW:
    def __enter__(self): pass
    def __exit__(self, *args): pass
    def commit(self): pass
    def rollback(self): pass

class DummyRepo:
    def __init__(self):
        self.providers = {}
        self.healths = {}
        self.blobs = {}

    def add(self, p): self.providers[p.provider_id] = p
    def get(self, pid): return self.providers.get(pid)
    def save(self, p): self.providers[p.provider_id] = p

    def add_health(self, h): self.healths[h.provider_id] = h
    def get_health(self, pid): return self.healths.get(pid)
    def save_health(self, h): self.healths[h.provider_id] = h

    def add_blob(self, b): self.blobs[b.blob_id] = b
    def get_blob(self, bid): return self.blobs.get(bid)

def test_registry_service():
    repo = DummyRepo()
    uow = DummyUoW()
    svc = ProviderRegistryService(repo, uow)

    p = svc.register_provider("p1", "Provider 1", "REST", {"key": "val"})
    assert p.enabled is True
    assert p.name == "Provider 1"
    
    events = p.pull_domain_events()
    assert len(events) == 1
    assert events[0].provider_id == "p1"
    assert events[0].event_name == "ProviderRegisteredEvent"

    svc.disable_provider("p1")
    assert repo.get("p1").enabled is False
    events = repo.get("p1").pull_domain_events()
    assert events[0].event_name == "ProviderDisabledEvent"

    svc.enable_provider("p1")
    assert repo.get("p1").enabled is True
    events = repo.get("p1").pull_domain_events()
    assert events[0].event_name == "ProviderEnabledEvent"
    
    assert svc.lookup_provider("p1") is not None
    
    # Disable already disabled
    svc.disable_provider("p1")
    svc.disable_provider("p1")
    svc.enable_provider("p1")
    svc.enable_provider("p1")
    
    svc.disable_provider("nonexistent")
    svc.enable_provider("nonexistent")

def test_health_service():
    repo = DummyRepo()
    uow = DummyUoW()
    svc = ProviderHealthService(repo, uow)

    assert svc.get_status("p2") == "UNKNOWN"

    svc.record_success("p2", 150)
    assert svc.get_status("p2") == "HEALTHY"
    
    svc.record_failure("p2")
    assert svc.get_status("p2") == "DEGRADED"

    svc.record_failure("p2")
    svc.record_failure("p2")
    assert svc.get_status("p2") == "UNAVAILABLE"
    
    h = repo.get_health("p2")
    events = h.pull_domain_events()
    assert len(events) > 0
    assert events[-1].event_name == "ProviderHealthChangedEvent"
    
    svc.record_success("p2", 120)
    assert svc.get_status("p2") == "HEALTHY"

def test_datalake_service():
    repo = DummyRepo()
    uow = DummyUoW()
    svc = DatalakeService(repo, uow)

    now = datetime.utcnow()
    blob = svc.persist_payload("p3", "a1", {"data": 1}, now)
    assert blob.provider_id == "p3"
    assert blob.asset_id == "a1"
    
    b2 = svc.retrieve_payload(blob.blob_id)
    assert b2 is not None
    assert b2.asset_id == "a1"

    events = blob.pull_domain_events()
    assert len(events) == 1
    assert events[0].event_name == "DatalakeBlobStoredEvent"
    
    # Test client abstract interface coverage
    c = DummyClient()
    c.fetch_asset("1")
    c.fetch_universe("1")
    c.health_check()
