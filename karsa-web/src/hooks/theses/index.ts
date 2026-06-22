import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { ThesesApi } from "../../api/endpoints/theses";
import { mapListTheses, mapThesisDetail } from "../../features/theses/utils/mappers";
import { ListThesesVM, ThesisDetailVM, ThesisLineageVM } from "../../features/theses/types/viewmodels";
import { ListThesesRequestDTO } from "../../types/theses/list-theses-request.dto";

export function useListTheses(params: ListThesesRequestDTO) {
  return useQuery<ListThesesVM, ApiError>({
    queryKey: queryKeys.theses.list(params),
    queryFn: async () => {
      const res = await ThesesApi.list(params);
      return mapListTheses(res);
    },
    staleTime: 30 * 1000,
  });
}

export function useThesisDetail(id: string) {
  return useQuery<ThesisDetailVM, ApiError>({
    queryKey: queryKeys.theses.detail(id),
    queryFn: async () => {
      const res = await ThesesApi.getById(id);
      return mapThesisDetail(res);
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useThesisLineage(id: string) {
  return useQuery<ThesisLineageVM, ApiError>({
    queryKey: queryKeys.theses.lineage(id),
    queryFn: async () => {
      const res = await ThesesApi.getLineage(id);
      return {
        sourceResearchIds: res.source_research_ids ?? [],
        decisionUrns: res.decision_urns ?? [],
        governanceReviewIds: res.governance_review_ids ?? [],
      };
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}
