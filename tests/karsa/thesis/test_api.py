import pytest
from fastapi.testclient import TestClient
from karsa.thesis.api.router import thesis_router, get_repo

client = TestClient(thesis_router)

class MockRepo:
    def get_all(self, limit, offset):
        from karsa.thesis.api.dtos import ThesisSummaryDto
        return [ThesisSummaryDto(urn="t:1", title="T", status="ACTIVE", version=1)]
    def get_by_urn(self, urn):
        return None

def override_get_repo():
    return MockRepo()

thesis_router.dependency_overrides[get_repo] = override_get_repo

def test_api_list():
    response = client.get("/thesis")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["urn"] == "t:1"

def test_api_detail_404():
    response = client.get("/thesis/missing")
    assert response.status_code == 404
