import { ResearchReportDTO } from "./research-report.dto";

export interface ListResearchReportsResponseDTO {
  data: ResearchReportDTO[];
  next_cursor?: string;
}
