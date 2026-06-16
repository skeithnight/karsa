import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { ResearchApi } from "../../api/endpoints/research";
import { mapListResearchReports } from "../../features/research/utils/mappers";
import { ListResearchReportsVM } from "../../features/research/types/viewmodels";
import { ListResearchReportsRequestDTO } from "../../types/research/list-research-reports-request.dto";

export function useListResearchReports(params: ListResearchReportsRequestDTO) {
  return useQuery<ListResearchReportsVM, ApiError>({
    queryKey: queryKeys.research.list(params),
    queryFn: async () => ({ data: [], total: 0 }),
    staleTime: 60 * 1000,
  });
}
