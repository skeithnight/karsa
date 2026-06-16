import { ApiClient } from "../client";
import { SearchRequestDTO } from "../../types/search/search-request.dto";
import { SearchResponseDTO } from "../../types/search/search-response.dto";
import { buildQueryString } from "../utils/query-string";

export const SearchApi = {
  query: (params: SearchRequestDTO): Promise<SearchResponseDTO> => {
    return ApiClient.fetch<SearchResponseDTO>(`/search${buildQueryString(params)}`);
  }
};
