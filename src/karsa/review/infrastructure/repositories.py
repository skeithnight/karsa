import os
import json
from typing import Optional, List, Dict
from karsa.review.domain.model.review import ReviewSession, LearningFeedback
from karsa.review.domain.model.repositories import (
    ReviewSessionRepository,
    LearningFeedbackRepository
)

class ConcurrencyConflictError(Exception):
    pass


class InMemoryReviewSessionRepository(ReviewSessionRepository):
    def __init__(self):
        self._sessions: Dict[str, ReviewSession] = {}

    def save(self, session: ReviewSession) -> None:
        existing = self._sessions.get(session.session_id)
        if existing:
            if existing.aggregate_version != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing.aggregate_version}, got {session.aggregate_version - 1}"
                )
        self._sessions[session.session_id] = ReviewSession.from_dict(session.to_dict())

    def find_by_id(self, session_id: str) -> Optional[ReviewSession]:
        # Return a copy to prevent in-place mutations outside save()
        session = self._sessions.get(session_id)
        return ReviewSession.from_dict(session.to_dict()) if session else None

    def list_all(self) -> List[ReviewSession]:
        return [ReviewSession.from_dict(s.to_dict()) for s in self._sessions.values()]

    def clear(self) -> None:
        self._sessions.clear()


class InMemoryLearningFeedbackRepository(LearningFeedbackRepository):
    def __init__(self):
        self._feedback: Dict[str, LearningFeedback] = {}

    def save(self, feedback: LearningFeedback) -> None:
        existing = self._feedback.get(feedback.feedback_id)
        if existing:
            if existing.aggregate_version != feedback.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing.aggregate_version}, got {feedback.aggregate_version - 1}"
                )
        self._feedback[feedback.feedback_id] = LearningFeedback.from_dict(feedback.to_dict())

    def find_by_id(self, feedback_id: str) -> Optional[LearningFeedback]:
        feed = self._feedback.get(feedback_id)
        return LearningFeedback.from_dict(feed.to_dict()) if feed else None

    def list_all(self) -> List[LearningFeedback]:
        return [LearningFeedback.from_dict(f.to_dict()) for f in self._feedback.values()]

    def clear(self) -> None:
        self._feedback.clear()


class FileReviewSessionRepository(ReviewSessionRepository):
    def __init__(self, storage_dir: str = ".karsa/review/sessions/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save(self, session: ReviewSession) -> None:
        path = self._get_path(session.session_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                existing_data = json.load(f)
            existing_ver = existing_data.get("aggregate_version", 1)
            if existing_ver != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing_ver}, got {session.aggregate_version - 1}"
                )
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def find_by_id(self, session_id: str) -> Optional[ReviewSession]:
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return ReviewSession.from_dict(data)

    def list_all(self) -> List[ReviewSession]:
        sessions = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    sessions.append(ReviewSession.from_dict(data))
                except Exception:
                    pass
        return sessions

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass


class FileLearningFeedbackRepository(LearningFeedbackRepository):
    def __init__(self, storage_dir: str = ".karsa/review/feedback/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, feedback_id: str) -> str:
        return os.path.join(self.storage_dir, f"{feedback_id}.json")

    def save(self, feedback: LearningFeedback) -> None:
        path = self._get_path(feedback.feedback_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                existing_data = json.load(f)
            existing_ver = existing_data.get("aggregate_version", 1)
            if existing_ver != feedback.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing_ver}, got {feedback.aggregate_version - 1}"
                )
        with open(path, "w") as f:
            json.dump(feedback.to_dict(), f, indent=2)

    def find_by_id(self, feedback_id: str) -> Optional[LearningFeedback]:
        path = self._get_path(feedback_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return LearningFeedback.from_dict(data)

    def list_all(self) -> List[LearningFeedback]:
        feedback_list = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    feedback_list.append(LearningFeedback.from_dict(data))
                except Exception:
                    pass
        return feedback_list

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass
