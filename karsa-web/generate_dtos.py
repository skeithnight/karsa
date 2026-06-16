import os

base_dir = "src/types"

files = {
    "common/pagination.dto.ts": """export interface PaginationRequestDTO {
  page: number;
  size: number;
}

export interface PaginationResponseDTO {
  total_elements: number;
  total_pages: number;
}
""",
    "common/error.dto.ts": """export interface ErrorResponseDTO {
  error_code: string;
  message: string;
  timestamp: string;
}
""",
    "portfolio/portfolio-summary-response.dto.ts": """export interface PortfolioSummaryResponseDTO {
  total_aum: number;
  daily_pnl: number;
  active_theses_count: number;
  net_exposure: number;
  last_updated: string;
}
""",
    "portfolio/portfolio-exposure-response.dto.ts": """export interface SectorExposureDTO {
  sector: string;
  allocation_pct: number;
}

export interface PortfolioExposureResponseDTO {
  sectors: SectorExposureDTO[];
}
""",
    "research/research-report.dto.ts": """export interface ResearchReportDTO {
  id: string;
  ticker: string;
  analyst_id: string;
  conviction: "HIGH" | "MED" | "LOW";
  summary: string;
  published_at: string;
}
""",
    "research/list-research-reports-request.dto.ts": """export interface ListResearchReportsRequestDTO {
  cursor?: string;
  limit?: number;
  ticker?: string;
  analyst?: string;
}
""",
    "research/list-research-reports-response.dto.ts": """import { ResearchReportDTO } from "./research-report.dto";

export interface ListResearchReportsResponseDTO {
  data: ResearchReportDTO[];
  next_cursor?: string;
}
""",
    "theses/thesis.dto.ts": """export interface ThesisDTO {
  thesis_urn: string;
  ticker: string;
  direction: "LONG" | "SHORT";
  state: "INITIATED" | "ACTIVE" | "INVALIDATED" | "EXPIRED";
  conviction_score: number;
  expected_horizon_days: number;
}
""",
    "theses/thesis-filter.dto.ts": """export interface ThesisFilterDTO {
  status?: string;
  ticker?: string;
}
""",
    "theses/thesis-sort.dto.ts": """export interface ThesisSortDTO {
  sort_by: "conviction" | "date" | "risk";
  direction: "asc" | "desc";
}
""",
    "theses/list-theses-request.dto.ts": """import { PaginationRequestDTO } from "../common/pagination.dto";
import { ThesisFilterDTO } from "./thesis-filter.dto";
import { ThesisSortDTO } from "./thesis-sort.dto";

export interface ListThesesRequestDTO {
  pagination: PaginationRequestDTO;
  filter?: ThesisFilterDTO;
  sort?: ThesisSortDTO;
}
""",
    "theses/list-theses-response.dto.ts": """import { PaginationResponseDTO } from "../common/pagination.dto";
import { ThesisDTO } from "./thesis.dto";

export interface ListThesesResponseDTO {
  data: ThesisDTO[];
  pagination: PaginationResponseDTO;
}
""",
    "theses/thesis-detail-response.dto.ts": """export interface ThesisDetailResponseDTO {
  thesis_urn: string;
  ticker: string;
  invalidation_criteria: string[];
}
""",
    "theses/thesis-lineage-response.dto.ts": """export interface ThesisLineageResponseDTO {
  source_research_ids: string[];
  decision_urns: string[];
  governance_review_ids: string[];
}
""",
    "memos/memo.dto.ts": """export interface DecisionMemoDTO {
  decision_urn: string;
  thesis_urn: string;
  intent: string;
  pep_signature: string;
  timestamp: string;
}
""",
    "memos/list-memos-request.dto.ts": """import { PaginationRequestDTO } from "../common/pagination.dto";

export interface ListMemosRequestDTO {
  pagination: PaginationRequestDTO;
  thesis_urn?: string;
}
""",
    "memos/list-memos-response.dto.ts": """import { PaginationResponseDTO } from "../common/pagination.dto";
import { DecisionMemoDTO } from "./memo.dto";

export interface ListMemosResponseDTO {
  data: DecisionMemoDTO[];
  pagination: PaginationResponseDTO;
}
""",
    "analysts/analyst-metric.dto.ts": """export interface AnalystMetricDTO {
  analyst_id: string;
  role: string;
  trust_score: number;
  win_rate: number;
  drawdown: number;
}
""",
    "analysts/list-analysts-response.dto.ts": """import { AnalystMetricDTO } from "./analyst-metric.dto";

export interface ListAnalystsResponseDTO {
  data: AnalystMetricDTO[];
}
""",
    "performance/attribution.dto.ts": """export interface AttributionDTO {
  date: string;
  selection_return: number;
  allocation_return: number;
  beta_return: number;
}
""",
    "performance/performance-request.dto.ts": """export interface PerformanceRequestDTO {
  start_date: string;
  end_date: string;
}
""",
    "performance/performance-response.dto.ts": """import { AttributionDTO } from "./attribution.dto";

export interface PerformanceResponseDTO {
  data: AttributionDTO[];
}
""",
    "governance/post-mortem.dto.ts": """export interface PostMortemDTO {
  id: string;
  thesis_urn: string;
  failure_reason: string;
  policy_overrides: boolean;
  timestamp: string;
}
""",
    "governance/list-post-mortems-request.dto.ts": """export interface ListPostMortemsRequestDTO {
  cursor?: string;
  limit?: number;
}
""",
    "governance/list-post-mortems-response.dto.ts": """import { PostMortemDTO } from "./post-mortem.dto";

export interface ListPostMortemsResponseDTO {
  data: PostMortemDTO[];
  next_cursor?: string;
}
""",
    "search/search-result.dto.ts": """export interface SearchResultDTO {
  type: "THESIS" | "RESEARCH" | "ANALYST" | "TICKER";
  id: string;
  label: string;
  route: string;
}
""",
    "search/search-request.dto.ts": """export interface SearchRequestDTO {
  q: string;
}
""",
    "search/search-response.dto.ts": """import { SearchResultDTO } from "./search-result.dto";

export interface SearchResponseDTO {
  results: SearchResultDTO[];
}
"""
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("DTO files generated successfully.")
