import { ApiClient } from "../client";
import { ListResearchReportsRequestDTO } from "../../types/research/list-research-reports-request.dto";
import { ListResearchReportsResponseDTO } from "../../types/research/list-research-reports-response.dto";
import { buildQueryString } from "../utils/query-string";

export const ResearchApi = {
  listReports: (params: ListResearchReportsRequestDTO): Promise<ListResearchReportsResponseDTO> => {
    return ApiClient.fetch<ListResearchReportsResponseDTO>(`/research/reports${buildQueryString(params)}`);
  }
};
