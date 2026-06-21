"""API integration tests — Sprint-10 Wave-7."""
import pytest
import json
from datetime import datetime
from typing import Optional, Dict, List

from karsa.review_engine.infrastructure.repositories.review_projection_repository import ReviewProjectionRepository
from karsa.review_engine.domain.aggregates.review_assessment import ReviewAssessment
from karsa.review_engine.domain.value_objects.enums import ReviewType
from karsa.review_engine.domain.value_objects.review_summary import ReviewSummary
from karsa.review_engine.domain.value_objects.review_quality import ReviewQuality
from karsa.review_engine.domain.value_objects.review_context_snapshot import ReviewContextSnapshot


# --- In-memory repositories for API tests ---

class InMemoryAssessmentRepository:
    def __init__(self):
        self._store: Dict[str, ReviewAssessment] = {}

    def save(self, record: ReviewAssessment) -> bool:
        self._store[record.review_id] = record
        return True

    def get_by_id(self, review_id: str):
        return self._store.get(review_id)

    def get_by_evaluation_and_type(self, evaluation_id: str, review_type: str):
        for r in self._store.values():
            if r.evaluation_id == evaluation_id and r.review_type.value == review_type:
                return r
        return None

    def get_by_target_urn(self, target_urn: str):
        return [r for r in self._store.values() if r.target_urn == target_urn]

    def list_reviews(self, page: int = 1, size: int = 50):
        items = sorted(self._store.values(), key=lambda r: r.created_at, reverse=True)
        offset = (page - 1) * size
        return items[offset:offset + size]


class InMemoryProjectionRepository:
    def __init__(self):
        self._worker_reviews: Dict[str, Dict] = {}
        self._thesis_reviews: Dict[str, Dict] = {}
        self._capability_gaps: Dict[str, List[Dict]] = {}
        self._review_coverage: Dict[str, Dict] = {}

    def add_worker_review(self, target_urn: str, total_reviews: int = 1,
                         avg_quality_score: float = 0.7, total_findings: int = 5,
                         total_recommendations: int = 3):
        self._worker_reviews[target_urn] = {
            "target_urn": target_urn,
            "total_reviews": total_reviews,
            "avg_quality_score": avg_quality_score,
            "total_findings": total_findings,
            "total_recommendations": total_recommendations,
            "last_reviewed": datetime.utcnow().isoformat(),
        }

    def add_thesis_review(self, thesis_urn: str, total_reviews: int = 1,
                         avg_quality_score: float = 0.8):
        self._thesis_reviews[thesis_urn] = {
            "thesis_urn": thesis_urn,
            "total_reviews": total_reviews,
            "avg_quality_score": avg_quality_score,
            "last_reviewed": datetime.utcnow().isoformat(),
        }

    def add_capability_gap(self, target_urn: str, gap_type: str, severity: str, description: str):
        if target_urn not in self._capability_gaps:
            self._capability_gaps[target_urn] = []
        self._capability_gaps[target_urn].append({
            "target_urn": target_urn,
            "gap_type": gap_type,
            "severity": severity,
            "description": description,
            "identified_at": datetime.utcnow().isoformat(),
        })

    def add_review_coverage(self, decision_id: str, review_type: str = "WORKER",
                           review_status: str = "COMPLETED"):
        self._review_coverage[decision_id] = {
            "decision_id": decision_id,
            "proposal_id": None,
            "cycle_id": None,
            "review_type": review_type,
            "review_status": review_status,
            "review_id": None,
            "review_due_date": None,
            "executed_at": datetime.utcnow().isoformat(),
            "days_overdue": None,
        }

    def get_worker_review(self, target_urn):
        return self._worker_reviews.get(target_urn)

    def get_thesis_review(self, thesis_urn):
        return self._thesis_reviews.get(thesis_urn)

    def get_capability_gaps(self, target_urn):
        return self._capability_gaps.get(target_urn, [])

    def get_review_coverage(self, evaluation_id):
        return self._review_coverage.get(evaluation_id)

    def list_all(self):
        return []


@pytest.fixture
def assessment_repo():
    return InMemoryAssessmentRepository()


@pytest.fixture
def projection_repo():
    return InMemoryProjectionRepository()


# --- Endpoint 1: Get Review by ID ---

class TestGetReviewEndpoint:
    def test_not_found(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/nonexistent")
        assert response.status_code == 404


# --- Endpoint 2: List Reviews ---

class TestListReviewsEndpoint:
    def test_list_reviews(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_pagination_validation(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews?page=0")
        assert response.status_code == 422
        response = client.get("/api/v1/reviews?size=101")
        assert response.status_code == 422


# --- Endpoint 3: Worker Review ---

class TestWorkerReviewEndpoint:
    def test_get_worker_review(self, projection_repo):
        projection_repo.add_worker_review("worker-1", 5, 0.7, 20, 8)
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/workers/worker-1")
        assert response.status_code == 200
        data = response.json()
        assert data["target_urn"] == "worker-1"
        assert data["total_reviews"] == 5
        assert data["avg_quality_score"] == 0.7

    def test_not_found(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/workers/nonexistent")
        assert response.status_code == 404


# --- Endpoint 4: Thesis Review ---

class TestThesisReviewEndpoint:
    def test_get_thesis_review(self, projection_repo):
        projection_repo.add_thesis_review("thesis-1", 3, 0.8)
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/theses/thesis-1")
        assert response.status_code == 200
        data = response.json()
        assert data["thesis_urn"] == "thesis-1"
        assert data["total_reviews"] == 3

    def test_not_found(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/theses/nonexistent")
        assert response.status_code == 404


# --- Endpoint 5: Capability Gaps ---

class TestCapabilityGapEndpoint:
    def test_get_gaps(self, projection_repo):
        projection_repo.add_capability_gap("worker-1", "SKILL_GAP", "HIGH", "Missing skills")
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/capability-gaps/worker-1")
        assert response.status_code == 200
        data = response.json()
        assert data["target_urn"] == "worker-1"
        assert data["total_gaps"] == 1

    def test_empty_gaps(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/capability-gaps/worker-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total_gaps"] == 0


# --- Endpoint 6: Coverage ---

class TestCoverageEndpoint:
    def test_get_coverage(self, projection_repo):
        projection_repo.add_review_coverage("eval-1", "WORKER", "COMPLETED")
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/coverage/eval-1")
        assert response.status_code == 200
        data = response.json()
        assert data["decision_id"] == "eval-1"
        assert data["review_type"] == "WORKER"
        assert data["review_status"] == "COMPLETED"

    def test_not_found(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/coverage/nonexistent")
        assert response.status_code == 404


# --- Endpoint 1: Get Review by ID ---

class TestGetReviewEndpoint:
    def test_not_found(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews/nonexistent")
        assert response.status_code == 404


# --- Endpoint 2: List Reviews ---

class TestListReviewsEndpoint:
    def test_list_reviews(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_pagination_validation(self, projection_repo):
        from karsa.review_engine.api.routes import init_routes
        import fastapi.testclient
        app = fastapi.FastAPI()
        init_routes(app, InMemoryAssessmentRepository(), projection_repo)
        client = fastapi.testclient.TestClient(app)
        response = client.get("/api/v1/reviews?page=0")
        assert response.status_code == 422
        response = client.get("/api/v1/reviews?size=101")
        assert response.status_code == 422
