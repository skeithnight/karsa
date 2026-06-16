export interface ResearchReportDTO {
  id: string;
  ticker: string;
  analyst_id: string;
  conviction: "HIGH" | "MED" | "LOW";
  summary: string;
  published_at: string;
}
