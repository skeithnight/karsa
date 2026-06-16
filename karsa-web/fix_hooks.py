import os
import glob
import re

# Fix query-keys.ts
query_keys_path = 'src/hooks/query-keys.ts'
with open(query_keys_path, 'w') as f:
    f.write("""import { ListThesesRequestDTO } from "../types/theses/list-theses-request.dto";
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
""")

# Fix all hook files
hook_files = glob.glob('src/hooks/*/index.ts')
for hook_file in hook_files:
    with open(hook_file, 'r') as f:
        content = f.read()
    
    # Replace useQuery<VM, Error> with useQuery<VM, ApiError>
    content = content.replace(", Error>", ", ApiError>")
    
    # Add import for ApiError if it's not there
    if 'ApiError' not in content:
        content = 'import { ApiError } from "../../api/errors/api-error";\n' + content
        
    with open(hook_file, 'w') as f:
        f.write(content)

print("Fixed")
