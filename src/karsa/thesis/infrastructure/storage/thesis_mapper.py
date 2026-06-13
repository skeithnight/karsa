from karsa.thesis.domain.model.thesis import (
    ActiveThesis,
    ThesisState,
    ThesisVersion,
    ThesisReview,
    ThesisInvalidationRule,
    ThesisDependencyEdge,
    ThesisDependencyGraph
)
from karsa.thesis.infrastructure.storage.thesis_records import (
    ThesisRecord,
    ThesisVersionRecord,
    ThesisReviewRecord,
    ThesisInvalidationRuleRecord,
    ThesisDependencyEdgeRecord,
    ThesisDependencyGraphRecord
)

class ThesisMapper:
    @staticmethod
    def to_record(thesis: ActiveThesis) -> ThesisRecord:
        versions = [
            ThesisVersionRecord(
                version_id=v.version_id,
                derived_from=v.derived_from,
                created_at=v.created_at,
                content_hash=v.content_hash
            ) for v in thesis.versions
        ]
        
        reviews = [
            ThesisReviewRecord(
                review_id=r.review_id,
                reviewer=r.reviewer,
                reviewed_at=r.reviewed_at,
                outcome=r.outcome,
                notes=r.notes
            ) for r in thesis.reviews
        ]
        
        rules = [
            ThesisInvalidationRuleRecord(
                rule_id=r.rule_id,
                metric_name=r.metric_name,
                threshold=r.threshold,
                comparator=r.comparator,
                is_breached=r.is_breached
            ) for r in thesis.invalidation_rules
        ]
        
        graph_record = None
        if thesis.dependency_graph:
            edges = [
                ThesisDependencyEdgeRecord(
                    dependency_thesis_id=e.dependency_thesis_id,
                    impact_weight=e.impact_weight,
                    description=e.description
                ) for e in thesis.dependency_graph.edges
            ]
            graph_record = ThesisDependencyGraphRecord(
                graph_id=thesis.dependency_graph.graph_id,
                edges=edges
            )
            
        return ThesisRecord(
            thesis_id=thesis.thesis_id,
            author=thesis.author,
            created_at=thesis.created_at,
            state=thesis.state.value,
            versions=versions,
            reviews=reviews,
            invalidation_rules=rules,
            dependency_graph=graph_record
        )

    @staticmethod
    def to_domain(record: ThesisRecord) -> ActiveThesis:
        thesis = ActiveThesis(
            thesis_id=record.thesis_id,
            author=record.author,
            created_at=record.created_at
        )
        # Override initial state
        thesis.state = ThesisState(record.state)
        
        thesis.versions = [
            ThesisVersion(
                version_id=v.version_id,
                derived_from=v.derived_from,
                created_at=v.created_at,
                content_hash=v.content_hash
            ) for v in record.versions
        ]
        
        thesis.reviews = [
            ThesisReview(
                review_id=r.review_id,
                reviewer=r.reviewer,
                reviewed_at=r.reviewed_at,
                outcome=r.outcome,
                notes=r.notes
            ) for r in record.reviews
        ]
        
        thesis.invalidation_rules = [
            ThesisInvalidationRule(
                rule_id=r.rule_id,
                metric_name=r.metric_name,
                threshold=r.threshold,
                comparator=r.comparator,
                is_breached=r.is_breached
            ) for r in record.invalidation_rules
        ]
        
        if record.dependency_graph:
            graph = ThesisDependencyGraph(graph_id=record.dependency_graph.graph_id)
            graph.edges = [
                ThesisDependencyEdge(
                    dependency_thesis_id=e.dependency_thesis_id,
                    impact_weight=e.impact_weight,
                    description=e.description
                ) for e in record.dependency_graph.edges
            ]
            thesis.dependency_graph = graph
            
        return thesis
