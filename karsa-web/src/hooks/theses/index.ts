import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { ThesesApi } from "../../api/endpoints/theses";
import { mapListTheses, mapThesisDetail, mapThesisLineage } from "../../features/theses/utils/mappers";
import { ListThesesVM, ThesisDetailVM, ThesisLineageVM } from "../../features/theses/types/viewmodels";
import { ListThesesRequestDTO } from "../../types/theses/list-theses-request.dto";

export function useListTheses(params: ListThesesRequestDTO) {
  return useQuery<ListThesesVM, ApiError>({
    queryKey: queryKeys.theses.list(params),
    queryFn: async () => ({ data: [], totalPages: 0, totalElements: 0 }),
    staleTime: 30 * 1000,
  });
}

export function useThesisDetail(id: string) {
  return useQuery<ThesisDetailVM, ApiError>({
    queryKey: queryKeys.theses.detail(id),
    queryFn: async () => ({ thesisUrn: id, ticker: "N/A", invalidationCriteria: [] }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useThesisLineage(id: string) {
  return useQuery<ThesisLineageVM, ApiError>({
    queryKey: queryKeys.theses.lineage(id),
    queryFn: async () => ({ sourceResearchIds: [], decisionUrns: [], governanceReviewIds: [] }),
    staleTime: 5 * 60 * 1000,
  });
}
