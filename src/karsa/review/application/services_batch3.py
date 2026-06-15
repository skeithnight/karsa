import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from karsa.review.domain.models import ReviewSession, ReviewRecord, PostMortemRecord
from karsa.review.domain.value_objects import (
    DecisionQualityAssessment,
    FailureClassification,
    SuccessClassification,
    ImprovementRecommendation,
    ReviewMethodologyManifest
)
from karsa.review.domain.events import (
    ReviewRecordRecordedEvent,
    FailureClassificationRecordedEvent,
    PostMortemFinalizedEvent
)


class MethodologyDriftException(Exception):
    pass


class ReplayIntegrityException(Exception):
    pass


def serialize_and_hash_inputs(
    decision_journal_data: Dict[str, Any],
    performance_data: Dict[str, Any],
    attribution_data: Dict[str, Any]
) -> str:
    # Combine them into a single structure
    payload = {
        "decision_journal": decision_journal_data,
        "performance": performance_data,
        "attribution": attribution_data
    }
    # Sort keys alphabetically and compute SHA-256 hash
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class ReviewRecordingService:
    def __init__(self, record_repo, session_repo, events_publisher: Optional[List[Any]] = None):
        self.record_repo = record_repo
        self.session_repo = session_repo
        self.events_publisher = events_publisher if events_publisher is not None else []

    def record_review(
        self,
        record_id: str,
        record_urn: str,
        session_urn: str,
        decision_id: str,
        worker_urn: str,
        review_methodology_urn: str,
        review_policy_hash: str,
        review_prompt_version: str,
        reviewer_model_version: str,
        review_methodology_manifest_hash: str,
        decision_quality: DecisionQualityAssessment,
        reviewed_at: datetime,
        review_version: int = 1,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> ReviewRecord:
        # Validate that the session exists and is in CONDUCTING state
        session = self.session_repo.find_by_urn(session_urn)
        if not session:
            raise ValueError(f"ReviewSession not found for URN: {session_urn}")
        if session.status != "CONDUCTING":
            raise ValueError(f"ReviewSession is not in CONDUCTING status (current: {session.status})")

        # Verify methodology manifest
        manifest = ReviewMethodologyManifest(
            review_methodology_urn=review_methodology_urn,
            review_policy_hash=review_policy_hash,
            review_prompt_version=review_prompt_version,
            reviewer_model_version=reviewer_model_version
        )
        computed = manifest.compute_hash()
        if computed != review_methodology_manifest_hash:
            raise ValueError("Methodology manifest hash mismatch")

        actual_reviewed_at = reviewed_at if reviewed_at is not None else datetime.now(timezone.utc)

        # Create the review record
        record = ReviewRecord(
            record_id=record_id,
            record_urn=record_urn,
            session_urn=session_urn,
            decision_id=decision_id,
            worker_urn=worker_urn,
            review_methodology_urn=review_methodology_urn,
            review_policy_hash=review_policy_hash,
            review_prompt_version=review_prompt_version,
            reviewer_model_version=reviewer_model_version,
            review_methodology_manifest_hash=review_methodology_manifest_hash,
            decision_quality=decision_quality,
            reviewed_at=actual_reviewed_at,
            review_version=review_version,
            is_active=True
        )

        # Check if there is an existing active ReviewRecord for this decision_id and worker_urn
        # If yes, we need to supersede it!
        existing_active = self.record_repo.find_active_by_worker(worker_urn, limit=100)
        for old_rec in existing_active:
            if old_rec.decision_id == decision_id and old_rec.is_active:
                old_rec.supersede(next_version=review_version)
                self.record_repo.save(old_rec)

        self.record_repo.save(record)

        # Publish ReviewRecordRecordedEvent
        evt = ReviewRecordRecordedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id or session.session_id,
            causation_id=causation_id or record.record_id,
            occurred_at=actual_reviewed_at,
            event_version=1,
            record_urn=record.record_urn,
            session_urn=record.session_urn,
            decision_id=record.decision_id,
            reviewer_urn=record.worker_urn,
            review_methodology_manifest_hash=record.review_methodology_manifest_hash,
            review_version=record.review_version
        )
        self.events_publisher.append(evt)
        return record


class ReviewReplayService:
    def __init__(self, record_repo, session_repo):
        self.record_repo = record_repo
        self.session_repo = session_repo

    def verify_methodology_manifest(self, record: ReviewRecord) -> None:
        manifest = ReviewMethodologyManifest(
            review_methodology_urn=record.review_methodology_urn,
            review_policy_hash=record.review_policy_hash,
            review_prompt_version=record.review_prompt_version,
            reviewer_model_version=record.reviewer_model_version
        )
        computed_hash = manifest.compute_hash()
        if computed_hash != record.review_methodology_manifest_hash:
            raise MethodologyDriftException(
                f"Methodology manifest hash mismatch! Pinned: {record.review_methodology_manifest_hash}, Recomputed: {computed_hash}"
            )

    def verify_replay_integrity(
        self,
        session_urn: str,
        decision_journal_data: Dict[str, Any],
        performance_data: Dict[str, Any],
        attribution_data: Dict[str, Any]
    ) -> None:
        session = self.session_repo.find_by_urn(session_urn)
        if not session:
            raise ValueError(f"ReviewSession not found for URN: {session_urn}")
            
        computed_hash = serialize_and_hash_inputs(
            decision_journal_data=decision_journal_data,
            performance_data=performance_data,
            attribution_data=attribution_data
        )
        if computed_hash != session.raw_input_manifest_hash:
            raise ReplayIntegrityException(
                f"Replay integrity verification failed: input manifest hash mismatch! "
                f"Session hash: {session.raw_input_manifest_hash}, Computed: {computed_hash}"
            )


class ConsensusSolver:
    def solve_consensus(
        self,
        records: List[ReviewRecord],
        failure_classifications: List[FailureClassification],
        success_classifications: List[SuccessClassification],
        recommendations: List[ImprovementRecommendation],
        reputation_weights: Optional[Dict[str, float]] = None
    ) -> tuple[FailureClassification, SuccessClassification, ImprovementRecommendation]:
        if not records:
            raise ValueError("No records provided for consensus solving")
        if len(records) != len(failure_classifications) or len(records) != len(success_classifications) or len(records) != len(recommendations):
            raise ValueError("Mismatch in length of inputs")

        weights = reputation_weights or {}
        
        # 1. Failure Classification Consensus
        fc_fields = ["thesis_error", "execution_error", "timing_error", "sizing_error", "calibration_error"]
        fc_results = {}
        for field in fc_fields:
            sum_true = 0.0
            sum_all = 0.0
            for i, rec in enumerate(records):
                w = weights.get(rec.worker_urn, 1.0)
                val = getattr(failure_classifications[i], field)
                if val:
                    sum_true += w
                sum_all += w
            fc_results[field] = (sum_true / sum_all > 0.5) if sum_all > 0 else False
        failure_consensus = FailureClassification(**fc_results)

        # 2. Success Classification Consensus
        sc_fields = ["alpha_generation", "execution_efficiency", "risk_mitigation"]
        sc_results = {}
        for field in sc_fields:
            sum_true = 0.0
            sum_all = 0.0
            for i, rec in enumerate(records):
                w = weights.get(rec.worker_urn, 1.0)
                val = getattr(success_classifications[i], field)
                if val:
                    sum_true += w
                sum_all += w
            sc_results[field] = (sum_true / sum_all > 0.5) if sum_all > 0 else False
        success_consensus = SuccessClassification(**sc_results)

        # 3. Improvement Recommendation Consensus
        severity_map = {
            "THESIS_SUSPEND_RECOMMENDED": 5,
            "THESIS_REVIEW_REQUIRED": 4,
            "RISK_CONTROL_WARNING": 3,
            "EXECUTION_WARNING": 2,
            "PROCESS_IMPROVEMENT_REQUIRED": 1
        }
        
        code_weights = {}
        for i, rec in enumerate(records):
            w = weights.get(rec.worker_urn, 1.0)
            code = recommendations[i].recommendation_code
            code_weights[code] = code_weights.get(code, 0.0) + w
            
        winning_code = None
        max_weight = -1.0
        for code, weight in code_weights.items():
            if weight > max_weight:
                max_weight = weight
                winning_code = code
            elif abs(weight - max_weight) < 1e-9:
                if severity_map.get(code, 0) > severity_map.get(winning_code, 0):
                    winning_code = code

        matching_recs = [recommendations[i] for i, rec in enumerate(records) if recommendations[i].recommendation_code == winning_code]
        winning_severity = max(matching_recs, key=lambda x: severity_map.get(x.recommendation_code, 0)).recommendation_severity
        
        all_actions = []
        for mr in matching_recs:
            for act in mr.thesis_refinement_actions:
                if act not in all_actions:
                    all_actions.append(act)
                    
        winning_category = matching_recs[0].recommendation_category
        
        recommendation_consensus = ImprovementRecommendation(
            recommendation_code=winning_code,
            recommendation_category=winning_category,
            recommendation_severity=winning_severity,
            thesis_refinement_actions=all_actions
        )

        return failure_consensus, success_consensus, recommendation_consensus


class PostMortemService:
    def __init__(self, postmortem_repo, record_repo, solver: ConsensusSolver, events_publisher: Optional[List[Any]] = None):
        self.postmortem_repo = postmortem_repo
        self.record_repo = record_repo
        self.solver = solver
        self.events_publisher = events_publisher if events_publisher is not None else []

    def finalize_postmortem(
        self,
        postmortem_id: str,
        postmortem_urn: str,
        session_urn: str,
        decision_id: str,
        consensus_methodology_urn: str,
        consensus_policy_hash: str,
        input_review_record_urns: List[str],
        failure_classifications: List[FailureClassification],
        success_classifications: List[SuccessClassification],
        recommendations: List[ImprovementRecommendation],
        reputation_weights: Optional[Dict[str, float]] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> PostMortemRecord:
        records = []
        for urn in input_review_record_urns:
            rec = self.record_repo.find_by_urn(urn)
            if not rec:
                raise ValueError(f"ReviewRecord not found: {urn}")
            records.append(rec)

        fc, sc, rec_consensus = self.solver.solve_consensus(
            records=records,
            failure_classifications=failure_classifications,
            success_classifications=success_classifications,
            recommendations=recommendations,
            reputation_weights=reputation_weights
        )

        sorted_input_urns = sorted(input_review_record_urns)

        postmortem = PostMortemRecord(
            postmortem_id=postmortem_id,
            postmortem_urn=postmortem_urn,
            session_urn=session_urn,
            decision_id=decision_id,
            consensus_methodology_urn=consensus_methodology_urn,
            consensus_policy_hash=consensus_policy_hash,
            input_review_record_urns=sorted_input_urns,
            failure_classification=fc,
            success_classification=sc,
            recommendation=rec_consensus,
            created_at=datetime.now(timezone.utc),
            postmortem_version=1,
            is_active=True
        )

        cursor = None
        while True:
            pms = self.postmortem_repo.find_by_session_paginated(session_urn, limit=100, cursor=cursor)
            if not pms:
                break
            for old_pm in pms:
                if old_pm.decision_id == decision_id and old_pm.is_active:
                    old_pm.supersede(next_version=1)
                    self.postmortem_repo.save(old_pm)
            cursor = pms[-1].postmortem_urn

        self.postmortem_repo.save(postmortem)

        evt = PostMortemFinalizedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id or session_urn,
            causation_id=causation_id or postmortem.postmortem_id,
            occurred_at=datetime.now(timezone.utc),
            event_version=1,
            postmortem_urn=postmortem.postmortem_urn,
            session_urn=postmortem.session_urn,
            decision_id=postmortem.decision_id,
            input_review_record_urns=postmortem.input_review_record_urns,
            postmortem_version=postmortem.postmortem_version,
            consensus_methodology_urn=postmortem.consensus_methodology_urn,
            consensus_policy_hash=postmortem.consensus_policy_hash
        )
        self.events_publisher.append(evt)
        
        fail_evt = FailureClassificationRecordedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id or session_urn,
            causation_id=causation_id or postmortem.postmortem_id,
            occurred_at=datetime.now(timezone.utc),
            event_version=1,
            decision_id=postmortem.decision_id,
            thesis_error=fc.thesis_error,
            execution_error=fc.execution_error,
            timing_error=fc.timing_error,
            sizing_error=fc.sizing_error,
            calibration_error=fc.calibration_error,
            recommendation_code=rec_consensus.recommendation_code,
            severity=rec_consensus.recommendation_severity
        )
        self.events_publisher.append(fail_evt)

        return postmortem


class ReviewInvalidationService:
    def __init__(self, record_repo, postmortem_repo):
        self.record_repo = record_repo
        self.postmortem_repo = postmortem_repo

    def invalidate_review_chain(self, start_record_urn: str, invalidating_version: int) -> List[ReviewRecord]:
        lineage = self.record_repo.find_review_lineage(start_record_urn)
        invalidated_records = []
        for record in lineage:
            if record.is_active:
                record.invalidate(invalidating_version)
                self.record_repo.save(record)
                invalidated_records.append(record)
        return invalidated_records

    def invalidate_postmortem_chain(self, start_postmortem_urn: str, invalidating_version: int) -> List[PostMortemRecord]:
        lineage = self.postmortem_repo.find_postmortem_lineage(start_postmortem_urn)
        invalidated_pms = []
        for pm in lineage:
            if pm.is_active:
                pm.invalidate(invalidating_version)
                self.postmortem_repo.save(pm)
                invalidated_pms.append(pm)
        return invalidated_pms
