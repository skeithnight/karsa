import { ListThesesRequestDTO } from "../types/theses/list-theses-request.dto";
import { ListResearchReportsRequestDTO } from "../types/research/list-research-reports-request.dto";
import { ListMemosRequestDTO } from "../types/memos/list-memos-request.dto";
import { PerformanceRequestDTO } from "../types/performance/performance-request.dto";
import { ListPostMortemsRequestDTO } from "../types/governance/list-post-mortems-request.dto";

export const queryKeys = {
  portfolio: {
    summary: () => ['portfolio', 'summary'] as const,
    exposure: () => ['portfolio', 'exposure'] as const,
  },
  theses: {
    list: (params: ListThesesRequestDTO) => ['theses', 'list', params] as const,
    detail: (id: string) => ['theses', 'detail', id] as const,
    lineage: (id: string) => ['theses', 'lineage', id] as const,
  },
  research: {
    list: (params: ListResearchReportsRequestDTO) => ['research', 'list', params] as const,
  },
  memos: {
    list: (params: ListMemosRequestDTO) => ['memos', 'list', params] as const,
  },
  analysts: {
    metrics: () => ['analysts', 'metrics'] as const,
  },
  performance: {
    attribution: (params: PerformanceRequestDTO) => ['performance', 'attribution', params] as const,
  },
  governance: {
    list: (params: ListPostMortemsRequestDTO) => ['governance', 'list', params] as const,
  },
  search: {
    results: (query: string) => ['search', 'results', query] as const,
  },
};
