import pytest
from typing import List

from karsa.allocation.application.port.memory_platform_port import MemoryPlatformPort, AllocationArtifactPayload
from karsa.allocation.application.service.allocation_application_service import AllocationApplicationService
from karsa.allocation.infrastructure.storage.in_memory_allocation_repository import InMemoryAllocationRepository
from karsa.allocation.domain.model.allocation import AllocationState

class InMemoryPlatformAdapter(MemoryPlatformPort):
    def __init__(self):
        self.published_artifacts: List[AllocationArtifactPayload] = []

    def publish_artifact(self, payload: AllocationArtifactPayload) -> None:
        self.published_artifacts.append(payload)

@pytest.fixture
def repo():
    return InMemoryAllocationRepository()

@pytest.fixture
def port():
    return InMemoryPlatformAdapter()

@pytest.fixture
def service(repo, port):
    return AllocationApplicationService(repository=repo, memory_port=port)

def test_allocation_lifecycle_publishes_artifacts(service, port, repo):
    # Create
    service.create_allocation("A-1", "T-1", 0.15, 0.10, 0.1, 5.0)
    assert len(port.published_artifacts) == 1
    assert port.published_artifacts[-1].event_type == "ALLOCATION_CREATED"
    assert port.published_artifacts[-1].state == "PENDING"
    
    saved = repo.get_by_id("A-1")
    assert saved.state == AllocationState.PENDING

    # Activate
    service.activate_allocation("A-1")
    assert len(port.published_artifacts) == 2
    assert port.published_artifacts[-1].event_type == "ALLOCATION_ACTIVATED"
    assert port.published_artifacts[-1].state == "ACTIVE"
    
    saved = repo.get_by_id("A-1")
    assert saved.state == AllocationState.ACTIVE

    # Scale
    service.scale_allocation_budget("A-1", 0.30)
    assert len(port.published_artifacts) == 3
    assert port.published_artifacts[-1].event_type == "ALLOCATION_SCALED"
    assert port.published_artifacts[-1].state == "ACTIVE"
    assert port.published_artifacts[-1].details["new_volatility_budget"] == pytest.approx(0.075)

    # Suspend
    service.suspend_allocation("A-1")
    assert len(port.published_artifacts) == 4
    assert port.published_artifacts[-1].event_type == "ALLOCATION_SUSPENDED"
    assert port.published_artifacts[-1].state == "SUSPENDED"

    # Terminate
    service.terminate_allocation("A-1")
    assert len(port.published_artifacts) == 5
    assert port.published_artifacts[-1].event_type == "ALLOCATION_TERMINATED"
    assert port.published_artifacts[-1].state == "TERMINATED"

def test_invalid_allocation_id_raises_error(service):
    with pytest.raises(ValueError):
        service.activate_allocation("NONEXISTENT")
