import { ApiClient } from "../client";
import { ListMemosRequestDTO } from "../../types/memos/list-memos-request.dto";
import { ListMemosResponseDTO } from "../../types/memos/list-memos-response.dto";
import { buildQueryString } from "../utils/query-string";

export const MemosApi = {
  list: (params: ListMemosRequestDTO): Promise<ListMemosResponseDTO> => {
    return ApiClient.fetch<ListMemosResponseDTO>(`/cio/decisions${buildQueryString(params)}`);
  }
};
