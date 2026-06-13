import pytest
from typing import List

from karsa.thesis.application.port.memory_platform_port import MemoryPlatformPort, ArtifactPayload
from karsa.thesis.application.service.thesis_application_service import ThesisApplicationService
from karsa.thesis.infrastructure.storage.in_memory_thesis_repository import InMemoryThesisRepository

class InMemoryPlatformAdapter(MemoryPlatformPort):
    def __init__(self):
        self.published_artifacts: List[ArtifactPayload] = []

    def publish_artifact(self, payload: ArtifactPayload) -> None:
        self.published_artifacts.append(payload)

@pytest.fixture
def repo():
    return InMemoryThesisRepository()

@pytest.fixture
def port():
    return InMemoryPlatformAdapter()

@pytest.fixture
def service(repo, port):
    return ThesisApplicationService(repository=repo, memory_port=port)

def test_thesis_lifecycle_publishes_artifacts(service, port):
    # ACTIVE
    service.create_thesis("T-1", "author1")
    assert len(port.published_artifacts) == 1
    assert port.published_artifacts[-1].event_type == "THESIS_CREATED"
    assert port.published_artifacts[-1].state == "ACTIVE"

    # ACTIVE -> DEGRADED
    service.degrade_thesis("T-1")
    assert len(port.published_artifacts) == 2
    assert port.published_artifacts[-1].event_type == "THESIS_DEGRADED"
    assert port.published_artifacts[-1].state == "DEGRADED"

    # DEGRADED -> UNDER_REVIEW
    service.request_review("T-1")
    assert len(port.published_artifacts) == 3
    assert port.published_artifacts[-1].event_type == "REVIEW_REQUESTED"
    assert port.published_artifacts[-1].state == "UNDER_REVIEW"

    # UNDER_REVIEW -> CONFIRMED
    service.confirm_thesis("T-1", "R-1", "reviewer1", "APPROVE", "looks good")
    assert len(port.published_artifacts) == 4
    assert port.published_artifacts[-1].event_type == "THESIS_CONFIRMED"
    assert port.published_artifacts[-1].state == "CONFIRMED"
    assert port.published_artifacts[-1].details["outcome"] == "APPROVE"

def test_thesis_under_review_to_invalidated(service, port):
    service.create_thesis("T-2", "author2")
    service.degrade_thesis("T-2")
    service.request_review("T-2")
    
    port.published_artifacts.clear()
    
    # UNDER_REVIEW -> INVALIDATED
    service.invalidate_thesis("T-2", "Fatal flaw")
    assert len(port.published_artifacts) == 1
    assert port.published_artifacts[-1].event_type == "THESIS_INVALIDATED"
    assert port.published_artifacts[-1].state == "INVALIDATED"
    assert port.published_artifacts[-1].details["reason"] == "Fatal flaw"

def test_thesis_under_review_to_retired(service, port):
    service.create_thesis("T-3", "author3")
    service.degrade_thesis("T-3")
    service.request_review("T-3")
    
    port.published_artifacts.clear()
    
    # UNDER_REVIEW -> RETIRED
    service.retire_thesis("T-3", "End of life")
    assert len(port.published_artifacts) == 1
    assert port.published_artifacts[-1].event_type == "THESIS_RETIRED"
    assert port.published_artifacts[-1].state == "RETIRED"
    assert port.published_artifacts[-1].details["reason"] == "End of life"

def test_invalid_thesis_id_raises_error(service):
    with pytest.raises(ValueError):
        service.degrade_thesis("NONEXISTENT")
