import { ApiClient } from "../client";
import { ListThesesRequestDTO } from "../../types/theses/list-theses-request.dto";
import { ListThesesResponseDTO } from "../../types/theses/list-theses-response.dto";
import { ThesisDetailResponseDTO } from "../../types/theses/thesis-detail-response.dto";
import { ThesisLineageResponseDTO } from "../../types/theses/thesis-lineage-response.dto";
import { buildQueryString } from "../utils/query-string";

export const ThesesApi = {
  list: (params: ListThesesRequestDTO): Promise<ListThesesResponseDTO> => {
    return ApiClient.fetch<ListThesesResponseDTO>(`/thesis${buildQueryString(params)}`);
  },
  getById: (id: string): Promise<ThesisDetailResponseDTO> => {
    return ApiClient.fetch<ThesisDetailResponseDTO>(`/thesis/${id}`);
  },
  getLineage: (id: string): Promise<ThesisLineageResponseDTO> => {
    return ApiClient.fetch<ThesisLineageResponseDTO>(`/theses/${id}/lineage`);
  }
};
