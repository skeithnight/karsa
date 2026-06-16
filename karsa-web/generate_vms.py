import os

files = {}

# Portfolio
files['src/features/portfolio/types/viewmodels.ts'] = """import { StatusBadge } from "../../../lib/formatters/status";

export interface PortfolioSummaryVM {
  totalAumRaw: number;
  totalAumDisplay: string;
  dailyPnlRaw: number;
  dailyPnlDisplay: string;
  activeThesesCount: number;
  netExposureRaw: number;
  netExposureDisplay: string;
  lastUpdatedRaw: string;
  lastUpdatedDisplay: string;
}

export interface SectorExposureVM {
  sector: string;
  allocationPctRaw: number;
  allocationPctDisplay: string;
}

export interface PortfolioExposureVM {
  sectors: SectorExposureVM[];
}
"""

files['src/features/portfolio/utils/mappers.ts'] = """import { PortfolioSummaryResponseDTO } from "../../../types/portfolio/portfolio-summary-response.dto";
import { PortfolioExposureResponseDTO, SectorExposureDTO } from "../../../types/portfolio/portfolio-exposure-response.dto";
import { formatCurrency } from "../../../lib/formatters/currency";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatDate } from "../../../lib/formatters/date";
import { PortfolioSummaryVM, PortfolioExposureVM, SectorExposureVM } from "../types/viewmodels";

export function mapPortfolioSummary(dto: PortfolioSummaryResponseDTO): PortfolioSummaryVM {
  return {
    totalAumRaw: dto.total_aum,
    totalAumDisplay: formatCurrency(dto.total_aum, "USD"),
    dailyPnlRaw: dto.daily_pnl,
    dailyPnlDisplay: formatCurrency(dto.daily_pnl, "USD"),
    activeThesesCount: dto.active_theses_count,
    netExposureRaw: dto.net_exposure,
    netExposureDisplay: formatPercentage(dto.net_exposure, 2),
    lastUpdatedRaw: dto.last_updated,
    lastUpdatedDisplay: formatDate(dto.last_updated, "short"),
  };
}

export function mapSectorExposure(dto: SectorExposureDTO): SectorExposureVM {
  return {
    sector: dto.sector,
    allocationPctRaw: dto.allocation_pct,
    allocationPctDisplay: formatPercentage(dto.allocation_pct, 2),
  };
}

export function mapPortfolioExposure(dto: PortfolioExposureResponseDTO): PortfolioExposureVM {
  return {
    sectors: dto.sectors.map(mapSectorExposure),
  };
}
"""

# Research
files['src/features/research/types/viewmodels.ts'] = """import { StatusBadge } from "../../../lib/formatters/status";

export interface ResearchReportVM {
  id: string;
  ticker: string;
  analystId: string;
  convictionRaw: string;
  convictionBadge: StatusBadge;
  summary: string;
  publishedAtRaw: string;
  publishedAtDisplay: string;
}

export interface ListResearchReportsVM {
  data: ResearchReportVM[];
  nextCursor?: string;
}
"""

files['src/features/research/utils/mappers.ts'] = """import { ResearchReportDTO } from "../../../types/research/research-report.dto";
import { ListResearchReportsResponseDTO } from "../../../types/research/list-research-reports-response.dto";
import { formatConviction } from "../../../lib/formatters/status";
import { formatDate } from "../../../lib/formatters/date";
import { ResearchReportVM, ListResearchReportsVM } from "../types/viewmodels";

export function mapResearchReport(dto: ResearchReportDTO): ResearchReportVM {
  return {
    id: dto.id,
    ticker: dto.ticker,
    analystId: dto.analyst_id,
    convictionRaw: dto.conviction,
    convictionBadge: formatConviction(dto.conviction),
    summary: dto.summary,
    publishedAtRaw: dto.published_at,
    publishedAtDisplay: formatDate(dto.published_at, "short"),
  };
}

export function mapListResearchReports(dto: ListResearchReportsResponseDTO): ListResearchReportsVM {
  return {
    data: dto.data.map(mapResearchReport),
    nextCursor: dto.next_cursor,
  };
}
"""

# Memos
files['src/features/memos/types/viewmodels.ts'] = """export interface InvestmentMemoVM {
  decisionUrn: string;
  thesisUrn: string;
  intent: string;
  pepSignature: string;
  timestampRaw: string;
  timestampDisplay: string;
}

export interface ListInvestmentMemosVM {
  data: InvestmentMemoVM[];
  totalPages: number;
  totalElements: number;
}
"""

files['src/features/memos/utils/mappers.ts'] = """import { DecisionMemoDTO } from "../../../types/memos/memo.dto";
import { ListMemosResponseDTO } from "../../../types/memos/list-memos-response.dto";
import { formatDate } from "../../../lib/formatters/date";
import { InvestmentMemoVM, ListInvestmentMemosVM } from "../types/viewmodels";

export function mapInvestmentMemo(dto: DecisionMemoDTO): InvestmentMemoVM {
  return {
    decisionUrn: dto.decision_urn,
    thesisUrn: dto.thesis_urn,
    intent: dto.intent,
    pepSignature: dto.pep_signature,
    timestampRaw: dto.timestamp,
    timestampDisplay: formatDate(dto.timestamp, "short"),
  };
}

export function mapListInvestmentMemos(dto: ListMemosResponseDTO): ListInvestmentMemosVM {
  return {
    data: dto.data.map(mapInvestmentMemo),
    totalPages: dto.pagination.total_pages,
    totalElements: dto.pagination.total_elements,
  };
}
"""

# Theses
files['src/features/theses/types/viewmodels.ts'] = """import { StatusBadge } from "../../../lib/formatters/status";

export interface ThesisVM {
  thesisUrn: string;
  ticker: string;
  direction: string;
  stateRaw: string;
  stateBadge: StatusBadge;
  convictionScoreRaw: number;
  convictionScoreDisplay: string;
  expectedHorizonDaysRaw: number;
  expectedHorizonDaysDisplay: string;
}

export interface ListThesesVM {
  data: ThesisVM[];
  totalPages: number;
  totalElements: number;
}

export interface ThesisDetailVM {
  thesisUrn: string;
  ticker: string;
  invalidationCriteria: string[];
}

export interface ThesisLineageVM {
  sourceResearchIds: string[];
  decisionUrns: string[];
  governanceReviewIds: string[];
}
"""

files['src/features/theses/utils/mappers.ts'] = """import { ThesisDTO } from "../../../types/theses/thesis.dto";
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
    data: dto.data.map(mapThesis),
    totalPages: dto.pagination.total_pages,
    totalElements: dto.pagination.total_elements,
  };
}

export function mapThesisDetail(dto: ThesisDetailResponseDTO): ThesisDetailVM {
  return {
    thesisUrn: dto.thesis_urn,
    ticker: dto.ticker,
    invalidationCriteria: dto.invalidation_criteria,
  };
}

export function mapThesisLineage(dto: ThesisLineageResponseDTO): ThesisLineageVM {
  return {
    sourceResearchIds: dto.source_research_ids,
    decisionUrns: dto.decision_urns,
    governanceReviewIds: dto.governance_review_ids,
  };
}
"""

# Analysts
files['src/features/analysts/types/viewmodels.ts'] = """import { StatusBadge } from "../../../lib/formatters/status";

export interface AnalystMetricVM {
  analystId: string;
  role: string;
  trustScoreRaw: number;
  trustScoreDisplay: string;
  winRateRaw: number;
  winRateDisplay: string;
  drawdownRaw: number;
  drawdownDisplay: string;
  performanceStatus: StatusBadge;
}

export interface ListAnalystsVM {
  data: AnalystMetricVM[];
}
"""

files['src/features/analysts/utils/mappers.ts'] = """import { AnalystMetricDTO } from "../../../types/analysts/analyst-metric.dto";
import { ListAnalystsResponseDTO } from "../../../types/analysts/list-analysts-response.dto";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatPerformanceState } from "../../../lib/formatters/performance";
import { AnalystMetricVM, ListAnalystsVM } from "../types/viewmodels";

export function mapAnalystMetric(dto: AnalystMetricDTO): AnalystMetricVM {
  // derive performance status
  let state = "NEUTRAL";
  if (dto.win_rate > 0.6) state = "OUTPERFORM";
  else if (dto.win_rate < 0.4) state = "UNDERPERFORM";

  return {
    analystId: dto.analyst_id,
    role: dto.role, // "worker" can be translated to "analyst" inherently via VM naming, but the value can be preserved or mapped
    trustScoreRaw: dto.trust_score,
    trustScoreDisplay: dto.trust_score.toString(),
    winRateRaw: dto.win_rate,
    winRateDisplay: formatPercentage(dto.win_rate, 1),
    drawdownRaw: dto.drawdown,
    drawdownDisplay: formatPercentage(dto.drawdown, 1),
    performanceStatus: formatPerformanceState(state),
  };
}

export function mapListAnalysts(dto: ListAnalystsResponseDTO): ListAnalystsVM {
  return {
    data: dto.data.map(mapAnalystMetric),
  };
}
"""

# Governance
files['src/features/governance/types/viewmodels.ts'] = """export interface InvestmentOversightVM {
  id: string;
  thesisUrn: string;
  failureReason: string;
  policyOverridesRaw: boolean;
  policyOverridesDisplay: string;
  timestampRaw: string;
  timestampDisplay: string;
}

export interface ListInvestmentOversightVM {
  data: InvestmentOversightVM[];
  nextCursor?: string;
}
"""

files['src/features/governance/utils/mappers.ts'] = """import { PostMortemDTO } from "../../../types/governance/post-mortem.dto";
import { ListPostMortemsResponseDTO } from "../../../types/governance/list-post-mortems-response.dto";
import { formatDate } from "../../../lib/formatters/date";
import { InvestmentOversightVM, ListInvestmentOversightVM } from "../types/viewmodels";

export function mapInvestmentOversight(dto: PostMortemDTO): InvestmentOversightVM {
  return {
    id: dto.id,
    thesisUrn: dto.thesis_urn,
    failureReason: dto.failure_reason,
    policyOverridesRaw: dto.policy_overrides,
    policyOverridesDisplay: dto.policy_overrides ? "Policy Override" : "Standard",
    timestampRaw: dto.timestamp,
    timestampDisplay: formatDate(dto.timestamp, "short"),
  };
}

export function mapListInvestmentOversight(dto: ListPostMortemsResponseDTO): ListInvestmentOversightVM {
  return {
    data: dto.data.map(mapInvestmentOversight),
    nextCursor: dto.next_cursor,
  };
}
"""

# Performance
files['src/features/performance/types/viewmodels.ts'] = """export interface AttributionVM {
  dateRaw: string;
  dateDisplay: string;
  selectionReturnRaw: number;
  selectionReturnDisplay: string;
  allocationReturnRaw: number;
  allocationReturnDisplay: string;
  betaReturnRaw: number;
  betaReturnDisplay: string;
}

export interface PerformanceAttributionVM {
  data: AttributionVM[];
}
"""

files['src/features/performance/utils/mappers.ts'] = """import { AttributionDTO } from "../../../types/performance/attribution.dto";
import { PerformanceResponseDTO } from "../../../types/performance/performance-response.dto";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { formatDate } from "../../../lib/formatters/date";
import { AttributionVM, PerformanceAttributionVM } from "../types/viewmodels";

export function mapAttribution(dto: AttributionDTO): AttributionVM {
  return {
    dateRaw: dto.date,
    dateDisplay: formatDate(dto.date, "short"),
    selectionReturnRaw: dto.selection_return,
    selectionReturnDisplay: formatPercentage(dto.selection_return, 2),
    allocationReturnRaw: dto.allocation_return,
    allocationReturnDisplay: formatPercentage(dto.allocation_return, 2),
    betaReturnRaw: dto.beta_return,
    betaReturnDisplay: formatPercentage(dto.beta_return, 2),
  };
}

export function mapPerformanceAttribution(dto: PerformanceResponseDTO): PerformanceAttributionVM {
  return {
    data: dto.data.map(mapAttribution),
  };
}
"""

# Search
files['src/features/search/types/viewmodels.ts'] = """export interface SearchResultVM {
  type: string;
  id: string;
  label: string;
  route: string;
}

export interface SearchVM {
  results: SearchResultVM[];
}
"""

files['src/features/search/utils/mappers.ts'] = """import { SearchResultDTO } from "../../../types/search/search-result.dto";
import { SearchResponseDTO } from "../../../types/search/search-response.dto";
import { SearchResultVM, SearchVM } from "../types/viewmodels";

export function mapSearchResult(dto: SearchResultDTO): SearchResultVM {
  return {
    type: dto.type, // Could map 'WORKER' to 'ANALYST' here if needed. The DTO currently uses 'ANALYST'.
    id: dto.id,
    label: dto.label,
    route: dto.route,
  };
}

export function mapSearchResponse(dto: SearchResponseDTO): SearchVM {
  return {
    results: dto.results.map(mapSearchResult),
  };
}
"""

for path, content in files.items():
    full_path = os.path.join(path)
    d = os.path.dirname(full_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("Generated all files")
