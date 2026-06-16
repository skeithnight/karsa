import os

files = {}

files['src/hooks/query-client.ts'] = """import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 1000 * 60, // 60s default
      gcTime: 1000 * 60 * 5, // 5m default
      refetchOnWindowFocus: false,
    },
  },
});
"""

files['src/hooks/query-keys.ts'] = """export const queryKeys = {
  portfolio: {
    summary: () => ['portfolio', 'summary'] as const,
    exposure: () => ['portfolio', 'exposure'] as const,
  },
  theses: {
    list: (params: any) => ['theses', 'list', params] as const,
    detail: (id: string) => ['theses', 'detail', id] as const,
    lineage: (id: string) => ['theses', 'lineage', id] as const,
  },
  research: {
    list: (params: any) => ['research', 'list', params] as const,
  },
  memos: {
    list: (params: any) => ['memos', 'list', params] as const,
  },
  analysts: {
    metrics: () => ['analysts', 'metrics'] as const,
  },
  performance: {
    attribution: (params: any) => ['performance', 'attribution', params] as const,
  },
  governance: {
    list: (params: any) => ['governance', 'list', params] as const,
  },
  search: {
    results: (query: string) => ['search', 'results', query] as const,
  },
};
"""

files['src/hooks/portfolio/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { PortfolioApi } from "../../api/endpoints/portfolio";
import { mapPortfolioSummary, mapPortfolioExposure } from "../../features/portfolio/utils/mappers";
import { PortfolioSummaryVM, PortfolioExposureVM } from "../../features/portfolio/types/viewmodels";

export function usePortfolioSummary() {
  return useQuery<PortfolioSummaryVM, Error>({
    queryKey: queryKeys.portfolio.summary(),
    queryFn: () => PortfolioApi.getSummary().then(mapPortfolioSummary),
    staleTime: 60 * 1000,
  });
}

export function usePortfolioExposure() {
  return useQuery<PortfolioExposureVM, Error>({
    queryKey: queryKeys.portfolio.exposure(),
    queryFn: () => PortfolioApi.getExposure().then(mapPortfolioExposure),
    staleTime: 5 * 60 * 1000,
  });
}
"""

files['src/hooks/theses/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { ThesesApi } from "../../api/endpoints/theses";
import { mapListTheses, mapThesisDetail, mapThesisLineage } from "../../features/theses/utils/mappers";
import { ListThesesVM, ThesisDetailVM, ThesisLineageVM } from "../../features/theses/types/viewmodels";
import { ListThesesRequestDTO } from "../../types/theses/list-theses-request.dto";

export function useListTheses(params: ListThesesRequestDTO) {
  return useQuery<ListThesesVM, Error>({
    queryKey: queryKeys.theses.list(params),
    queryFn: () => ThesesApi.list(params).then(mapListTheses),
    staleTime: 30 * 1000,
  });
}

export function useThesisDetail(id: string) {
  return useQuery<ThesisDetailVM, Error>({
    queryKey: queryKeys.theses.detail(id),
    queryFn: () => ThesesApi.getById(id).then(mapThesisDetail),
    staleTime: 5 * 60 * 1000,
  });
}

export function useThesisLineage(id: string) {
  return useQuery<ThesisLineageVM, Error>({
    queryKey: queryKeys.theses.lineage(id),
    queryFn: () => ThesesApi.getLineage(id).then(mapThesisLineage),
    staleTime: 5 * 60 * 1000,
  });
}
"""

files['src/hooks/research/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { ResearchApi } from "../../api/endpoints/research";
import { mapListResearchReports } from "../../features/research/utils/mappers";
import { ListResearchReportsVM } from "../../features/research/types/viewmodels";
import { ListResearchReportsRequestDTO } from "../../types/research/list-research-reports-request.dto";

export function useListResearchReports(params: ListResearchReportsRequestDTO) {
  return useQuery<ListResearchReportsVM, Error>({
    queryKey: queryKeys.research.list(params),
    queryFn: () => ResearchApi.listReports(params).then(mapListResearchReports),
    staleTime: 60 * 1000,
  });
}
"""

files['src/hooks/memos/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { MemosApi } from "../../api/endpoints/memos";
import { mapListInvestmentMemos } from "../../features/memos/utils/mappers";
import { ListInvestmentMemosVM } from "../../features/memos/types/viewmodels";
import { ListMemosRequestDTO } from "../../types/memos/list-memos-request.dto";

export function useListMemos(params: ListMemosRequestDTO) {
  return useQuery<ListInvestmentMemosVM, Error>({
    queryKey: queryKeys.memos.list(params),
    queryFn: () => MemosApi.list(params).then(mapListInvestmentMemos),
    staleTime: 60 * 1000,
  });
}
"""

files['src/hooks/analysts/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { AnalystsApi } from "../../api/endpoints/analysts";
import { mapListAnalysts } from "../../features/analysts/utils/mappers";
import { ListAnalystsVM } from "../../features/analysts/types/viewmodels";

export function useAnalystsMetrics() {
  return useQuery<ListAnalystsVM, Error>({
    queryKey: queryKeys.analysts.metrics(),
    queryFn: () => AnalystsApi.listMetrics().then(mapListAnalysts),
    staleTime: 60 * 1000,
  });
}
"""

files['src/hooks/performance/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { PerformanceApi } from "../../api/endpoints/performance";
import { mapPerformanceAttribution } from "../../features/performance/utils/mappers";
import { PerformanceAttributionVM } from "../../features/performance/types/viewmodels";
import { PerformanceRequestDTO } from "../../types/performance/performance-request.dto";

export function usePerformanceAttribution(params: PerformanceRequestDTO) {
  return useQuery<PerformanceAttributionVM, Error>({
    queryKey: queryKeys.performance.attribution(params),
    queryFn: () => PerformanceApi.getAttribution(params).then(mapPerformanceAttribution),
    staleTime: 5 * 60 * 1000,
  });
}
"""

files['src/hooks/governance/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { GovernanceApi } from "../../api/endpoints/governance";
import { mapListInvestmentOversight } from "../../features/governance/utils/mappers";
import { ListInvestmentOversightVM } from "../../features/governance/types/viewmodels";
import { ListPostMortemsRequestDTO } from "../../types/governance/list-post-mortems-request.dto";

export function useGovernancePostMortems(params: ListPostMortemsRequestDTO) {
  return useQuery<ListInvestmentOversightVM, Error>({
    queryKey: queryKeys.governance.list(params),
    queryFn: () => GovernanceApi.listPostMortems(params).then(mapListInvestmentOversight),
    staleTime: 60 * 1000,
  });
}
"""

files['src/hooks/search/index.ts'] = """import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { SearchApi } from "../../api/endpoints/search";
import { mapSearchResponse } from "../../features/search/utils/mappers";
import { SearchVM } from "../../features/search/types/viewmodels";

export function useSearch(query: string) {
  return useQuery<SearchVM, Error>({
    queryKey: queryKeys.search.results(query),
    queryFn: () => SearchApi.query({ q: query }).then(mapSearchResponse),
    staleTime: 10 * 1000,
    enabled: query !== undefined && query.length >= 2,
  });
}
"""

for path, content in files.items():
    full_path = os.path.join(path)
    d = os.path.dirname(full_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("Generated hook files")
