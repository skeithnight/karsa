import { ApiClient } from "../client";
import { ListPostMortemsRequestDTO } from "../../types/governance/list-post-mortems-request.dto";
import { ListPostMortemsResponseDTO } from "../../types/governance/list-post-mortems-response.dto";
import { buildQueryString } from "../utils/query-string";

export const GovernanceApi = {
  listPostMortems: (params: ListPostMortemsRequestDTO): Promise<ListPostMortemsResponseDTO> => {
    return ApiClient.fetch<ListPostMortemsResponseDTO>(`/post-mortem/records${buildQueryString(params)}`);
  }
};
