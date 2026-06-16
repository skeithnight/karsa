import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { MemosApi } from "../../api/endpoints/memos";
import { mapListInvestmentMemos } from "../../features/memos/utils/mappers";
import { ListInvestmentMemosVM } from "../../features/memos/types/viewmodels";
import { ListMemosRequestDTO } from "../../types/memos/list-memos-request.dto";

export function useListMemos(params: ListMemosRequestDTO) {
  return useQuery<ListInvestmentMemosVM, ApiError>({
    queryKey: queryKeys.memos.list(params),
    queryFn: () => MemosApi.list(params).then(mapListInvestmentMemos),
    staleTime: 60 * 1000,
  });
}
