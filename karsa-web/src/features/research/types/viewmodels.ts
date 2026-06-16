import { StatusBadge } from "../../../lib/formatters/status";

export interface ResearchReportVM {
  id: string;
  ticker: string;
  analystId: string;
  convictionRaw: string;
  convictionBadge: StatusBadge;
  summary: string;
  publishedAtRaw: string;
  publishedAtDisplay: string;
}

export interface ListResearchReportsVM {
  data: ResearchReportVM[];
  nextCursor?: string;
}
