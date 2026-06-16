import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { GovernanceApi } from "../../api/endpoints/governance";
import { mapListInvestmentOversight } from "../../features/governance/utils/mappers";
import { ListInvestmentOversightVM } from "../../features/governance/types/viewmodels";
import { ListPostMortemsRequestDTO } from "../../types/governance/list-post-mortems-request.dto";

export function useGovernancePostMortems(params: ListPostMortemsRequestDTO) {
  return useQuery<ListInvestmentOversightVM, ApiError>({
    queryKey: queryKeys.governance.list(params),
    queryFn: () => GovernanceApi.listPostMortems(params).then(mapListInvestmentOversight),
    staleTime: 60 * 1000,
  });
}
