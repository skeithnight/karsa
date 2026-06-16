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
    queryFn: () => ThesesApi.list(params).then(mapListTheses),
    staleTime: 30 * 1000,
  });
}

export function useThesisDetail(id: string) {
  return useQuery<ThesisDetailVM, ApiError>({
    queryKey: queryKeys.theses.detail(id),
    queryFn: () => ThesesApi.getById(id).then(mapThesisDetail),
    staleTime: 5 * 60 * 1000,
  });
}

export function useThesisLineage(id: string) {
  return useQuery<ThesisLineageVM, ApiError>({
    queryKey: queryKeys.theses.lineage(id),
    queryFn: () => ThesesApi.getLineage(id).then(mapThesisLineage),
    staleTime: 5 * 60 * 1000,
  });
}
