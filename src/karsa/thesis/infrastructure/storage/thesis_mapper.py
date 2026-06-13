from typing import Any, Dict
from karsa.thesis.domain.model.thesis import Thesis
from karsa.thesis.domain.model.value_objects import (
    ThesisState, HypothesisStructure, TimeHorizon, ResearchReference,
    ConfidenceModel, ThesisContributor, TimeClassification, ContributionRole, ConfidenceSource
)
from karsa.shared.domain.identity import OriginatorIdentity

class ThesisMapper:
    @staticmethod
    def to_payload(thesis: Thesis) -> Dict[str, Any]:
        return {
            "originator": {
                "originator_id": thesis.originator.originator_id,
                "originator_type": thesis.originator.originator_type,
                "originator_version": thesis.originator.originator_version,
                "originator_worker_id": thesis.originator.originator_worker_id,
                "originator_model": thesis.originator.originator_model,
                "originator_strategy": thesis.originator.originator_strategy
            },
            "hypothesis": {
                "hypothesis_statement": thesis.hypothesis.hypothesis_statement,
                "bull_case": thesis.hypothesis.bull_case,
                "bear_case": thesis.hypothesis.bear_case,
                "assumptions": thesis.hypothesis.assumptions,
                "expected_outcome": thesis.hypothesis.expected_outcome,
                "invalidation_criteria": thesis.hypothesis.invalidation_criteria,
                "success_criteria": thesis.hypothesis.success_criteria
            },
            "confidence": {
                "raw_confidence": thesis.confidence.raw_confidence,
                "calibrated_confidence": thesis.confidence.calibrated_confidence,
                "confidence_source": thesis.confidence.confidence_source.value,
                "confidence_updated_at": thesis.confidence.confidence_updated_at
            },
            "time_horizon": {
                "start_date": thesis.time_horizon.start_date,
                "target_date": thesis.time_horizon.target_date,
                "classification": thesis.time_horizon.classification.value
            },
            "research_lineage": [
                {
                    "research_id": r.research_id,
                    "research_version": r.research_version,
                    "research_type": r.research_type
                } for r in thesis.research_lineage
            ],
            "contributors": [
                {
                    "contributor_id": c.contributor_id,
                    "contributor_type": c.contributor_type,
                    "contribution_role": c.contribution_role.value
                } for c in thesis.contributors
            ]
        }

    @staticmethod
    def to_domain(row: tuple) -> Thesis:
        thesis_id = row[0]
        state = ThesisState(row[1])
        version = row[2]
        payload = row[3]
        if isinstance(payload, str):
            import json
            payload = json.loads(payload)
            
        originator_dict = payload["originator"]
        originator = OriginatorIdentity(
            originator_id=originator_dict["originator_id"],
            originator_type=originator_dict["originator_type"],
            originator_version=originator_dict["originator_version"],
            originator_worker_id=originator_dict.get("originator_worker_id"),
            originator_model=originator_dict.get("originator_model"),
            originator_strategy=originator_dict.get("originator_strategy")
        )
        
        hyp_dict = payload["hypothesis"]
        hypothesis = HypothesisStructure(
            hypothesis_statement=hyp_dict["hypothesis_statement"],
            bull_case=hyp_dict["bull_case"],
            bear_case=hyp_dict["bear_case"],
            assumptions=hyp_dict["assumptions"],
            expected_outcome=hyp_dict["expected_outcome"],
            invalidation_criteria=hyp_dict["invalidation_criteria"],
            success_criteria=hyp_dict["success_criteria"]
        )
        
        conf_dict = payload["confidence"]
        confidence = ConfidenceModel(
            raw_confidence=conf_dict["raw_confidence"],
            calibrated_confidence=conf_dict.get("calibrated_confidence"),
            confidence_source=ConfidenceSource(conf_dict["confidence_source"]),
            confidence_updated_at=conf_dict["confidence_updated_at"]
        )
        
        time_dict = payload["time_horizon"]
        time_horizon = TimeHorizon(
            start_date=time_dict["start_date"],
            target_date=time_dict["target_date"],
            classification=TimeClassification(time_dict["classification"])
        )
        
        research_lineage = [
            ResearchReference(
                research_id=r["research_id"],
                research_version=r["research_version"],
                research_type=r["research_type"]
            ) for r in payload.get("research_lineage", [])
        ]
        
        contributors = [
            ThesisContributor(
                contributor_id=c["contributor_id"],
                contributor_type=c["contributor_type"],
                contribution_role=ContributionRole(c["contribution_role"])
            ) for c in payload.get("contributors", [])
        ]
        
        return Thesis(
            thesis_id=thesis_id,
            originator=originator,
            hypothesis=hypothesis,
            confidence=confidence,
            time_horizon=time_horizon,
            research_lineage=research_lineage,
            contributors=contributors,
            state=state,
            aggregate_version=version
        )
