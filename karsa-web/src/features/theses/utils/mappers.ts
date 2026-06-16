import { ThesisDTO } from "../../../types/theses/thesis.dto";
import { ListThesesResponseDTO } from "../../../types/theses/list-theses-response.dto";
import { ThesisDetailResponseDTO } from "../../../types/theses/thesis-detail-response.dto";
import { ThesisLineageResponseDTO } from "../../../types/theses/thesis-lineage-response.dto";
import { formatStatus } from "../../../lib/formatters/status";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { ThesisVM, ListThesesVM, ThesisDetailVM, ThesisLineageVM } from "../types/viewmodels";

export function mapThesis(dto: ThesisDTO): ThesisVM {
  return {
    thesisUrn: dto.thesis_urn,
    ticker: dto.ticker,
    direction: dto.direction,
    stateRaw: dto.state,
    stateBadge: formatStatus(dto.state),
    convictionScoreRaw: dto.conviction_score,
    convictionScoreDisplay: dto.conviction_score.toString(), // assuming raw score
    expectedHorizonDaysRaw: dto.expected_horizon_days,
    expectedHorizonDaysDisplay: `${dto.expected_horizon_days} days`,
  };
}

export function mapListTheses(dto: ListThesesResponseDTO): ListThesesVM {
  return {
    data: (dto.data ?? []).map(mapThesis),
    totalPages: dto.pagination?.total_pages ?? 1,
    totalElements: dto.pagination?.total_elements ?? 0,
  };
}

export function mapThesisDetail(dto: ThesisDetailResponseDTO): ThesisDetailVM {
  return {
    thesisUrn: dto.thesis_urn,
    ticker: dto.ticker,
    invalidationCriteria: dto.invalidation_criteria ?? [],
  };
}

export function mapThesisLineage(dto: ThesisLineageResponseDTO): ThesisLineageVM {
  return {
    sourceResearchIds: dto.source_research_ids ?? [],
    decisionUrns: dto.decision_urns ?? [],
    governanceReviewIds: dto.governance_review_ids ?? [],
  };
}
