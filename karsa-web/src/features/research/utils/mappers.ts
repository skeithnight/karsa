import { ResearchReportDTO } from "../../../types/research/research-report.dto";
import { ListResearchReportsResponseDTO } from "../../../types/research/list-research-reports-response.dto";
import { formatConviction } from "../../../lib/formatters/status";
import { formatDate } from "../../../lib/formatters/date";
import { ResearchReportVM, ListResearchReportsVM } from "../types/viewmodels";

export function mapResearchReport(dto: ResearchReportDTO): ResearchReportVM {
  return {
    id: dto.id,
    ticker: dto.ticker,
    analystId: dto.analyst_id,
    convictionRaw: dto.conviction,
    convictionBadge: formatConviction(dto.conviction),
    summary: dto.summary,
    publishedAtRaw: dto.published_at,
    publishedAtDisplay: formatDate(dto.published_at, "short"),
  };
}

export function mapListResearchReports(dto: ListResearchReportsResponseDTO): ListResearchReportsVM {
  return {
    data: (dto.data ?? []).map(mapResearchReport),
    nextCursor: dto.next_cursor,
  };
}
