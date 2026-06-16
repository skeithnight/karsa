import os

base_dir = "src/api"

files = {
    "client.ts": """export class ApiClient {
  private static baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  static async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `API Error: ${response.status} ${response.statusText}`);
    }
    return response.json() as Promise<T>;
  }
}
""",
    "errors/api-error.ts": """export class ApiError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}
""",
    "utils/query-string.ts": """export function buildQueryString(params: Record<string, any>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      if (typeof value === 'object') {
        // Flat nesting for simple DTOs (e.g. pagination.page -> page)
        for (const [subKey, subValue] of Object.entries(value)) {
           if (subValue !== undefined && subValue !== null) {
              query.append(subKey, String(subValue));
           }
        }
      } else {
        query.append(key, String(value));
      }
    }
  }
  const str = query.toString();
  return str ? `?${str}` : '';
}
""",
    "endpoints/portfolio.ts": """import { ApiClient } from "../client";
import { PortfolioSummaryResponseDTO } from "../../types/portfolio/portfolio-summary-response.dto";
import { PortfolioExposureResponseDTO } from "../../types/portfolio/portfolio-exposure-response.dto";

export const PortfolioApi = {
  getSummary: (): Promise<PortfolioSummaryResponseDTO> => {
    return ApiClient.fetch<PortfolioSummaryResponseDTO>("/portfolio/summary");
  },
  getExposure: (): Promise<PortfolioExposureResponseDTO> => {
    return ApiClient.fetch<PortfolioExposureResponseDTO>("/portfolio/exposure");
  }
};
""",
    "endpoints/research.ts": """import { ApiClient } from "../client";
import { ListResearchReportsRequestDTO } from "../../types/research/list-research-reports-request.dto";
import { ListResearchReportsResponseDTO } from "../../types/research/list-research-reports-response.dto";
import { buildQueryString } from "../utils/query-string";

export const ResearchApi = {
  listReports: (params: ListResearchReportsRequestDTO): Promise<ListResearchReportsResponseDTO> => {
    return ApiClient.fetch<ListResearchReportsResponseDTO>(`/research/reports${buildQueryString(params)}`);
  }
};
""",
    "endpoints/theses.ts": """import { ApiClient } from "../client";
import { ListThesesRequestDTO } from "../../types/theses/list-theses-request.dto";
import { ListThesesResponseDTO } from "../../types/theses/list-theses-response.dto";
import { ThesisDetailResponseDTO } from "../../types/theses/thesis-detail-response.dto";
import { ThesisLineageResponseDTO } from "../../types/theses/thesis-lineage-response.dto";
import { buildQueryString } from "../utils/query-string";

export const ThesesApi = {
  list: (params: ListThesesRequestDTO): Promise<ListThesesResponseDTO> => {
    return ApiClient.fetch<ListThesesResponseDTO>(`/theses${buildQueryString(params)}`);
  },
  getById: (id: string): Promise<ThesisDetailResponseDTO> => {
    return ApiClient.fetch<ThesisDetailResponseDTO>(`/theses/${id}`);
  },
  getLineage: (id: string): Promise<ThesisLineageResponseDTO> => {
    return ApiClient.fetch<ThesisLineageResponseDTO>(`/theses/${id}/lineage`);
  }
};
""",
    "endpoints/memos.ts": """import { ApiClient } from "../client";
import { ListMemosRequestDTO } from "../../types/memos/list-memos-request.dto";
import { ListMemosResponseDTO } from "../../types/memos/list-memos-response.dto";
import { buildQueryString } from "../utils/query-string";

export const MemosApi = {
  list: (params: ListMemosRequestDTO): Promise<ListMemosResponseDTO> => {
    return ApiClient.fetch<ListMemosResponseDTO>(`/decisions${buildQueryString(params)}`);
  }
};
""",
    "endpoints/analysts.ts": """import { ApiClient } from "../client";
import { ListAnalystsResponseDTO } from "../../types/analysts/list-analysts-response.dto";

export const AnalystsApi = {
  listMetrics: (): Promise<ListAnalystsResponseDTO> => {
    return ApiClient.fetch<ListAnalystsResponseDTO>("/workers/metrics");
  }
};
""",
    "endpoints/performance.ts": """import { ApiClient } from "../client";
import { PerformanceRequestDTO } from "../../types/performance/performance-request.dto";
import { PerformanceResponseDTO } from "../../types/performance/performance-response.dto";
import { buildQueryString } from "../utils/query-string";

export const PerformanceApi = {
  getAttribution: (params: PerformanceRequestDTO): Promise<PerformanceResponseDTO> => {
    return ApiClient.fetch<PerformanceResponseDTO>(`/performance/attribution${buildQueryString(params)}`);
  }
};
""",
    "endpoints/governance.ts": """import { ApiClient } from "../client";
import { ListPostMortemsRequestDTO } from "../../types/governance/list-post-mortems-request.dto";
import { ListPostMortemsResponseDTO } from "../../types/governance/list-post-mortems-response.dto";
import { buildQueryString } from "../utils/query-string";

export const GovernanceApi = {
  listPostMortems: (params: ListPostMortemsRequestDTO): Promise<ListPostMortemsResponseDTO> => {
    return ApiClient.fetch<ListPostMortemsResponseDTO>(`/governance/postmortems${buildQueryString(params)}`);
  }
};
""",
    "endpoints/search.ts": """import { ApiClient } from "../client";
import { SearchRequestDTO } from "../../types/search/search-request.dto";
import { SearchResponseDTO } from "../../types/search/search-response.dto";
import { buildQueryString } from "../utils/query-string";

export const SearchApi = {
  query: (params: SearchRequestDTO): Promise<SearchResponseDTO> => {
    return ApiClient.fetch<SearchResponseDTO>(`/search${buildQueryString(params)}`);
  }
};
"""
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("API files generated successfully.")
