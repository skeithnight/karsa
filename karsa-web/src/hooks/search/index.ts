import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { SearchApi } from "../../api/endpoints/search";
import { mapSearchResponse } from "../../features/search/utils/mappers";
import { SearchVM } from "../../features/search/types/viewmodels";

export function useSearch(query: string) {
  return useQuery<SearchVM, ApiError>({
    queryKey: queryKeys.search.results(query),
    queryFn: () => SearchApi.query({ q: query }).then(mapSearchResponse),
    staleTime: 10 * 1000,
    enabled: query !== undefined && query.length >= 2,
  });
}
