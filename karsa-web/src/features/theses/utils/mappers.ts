import { ThesisDTO } from "../../../types/theses/thesis.dto";
import { ListThesesResponseDTO } from "../../../types/theses/list-theses-response.dto";
import { ThesisDetailResponseDTO } from "../../../types/theses/thesis-detail-response.dto";
import { ThesisLineageResponseDTO } from "../../../types/theses/thesis-lineage-response.dto";
import { formatStatus } from "../../../lib/formatters/status";
import { formatPercentage } from "../../../lib/formatters/percentage";
import { ThesisVM, ListThesesVM, ThesisDetailVM } from "../types/viewmodels";

export function mapListTheses(dto: any): ListThesesVM {
  // If backend returns Array, handle it. If it returns { data: [] }, handle it.
  const dataArray = Array.isArray(dto) ? dto : (dto.data ?? []);
  return {
    data: dataArray.map((item: any) => ({
      urn: item.urn,
      title: item.title,
      status: item.status,
      confidence: item.confidence,
      version: item.version,
      author_urn: item.author_urn,
      regime_urn: item.regime_urn,
    })),
    totalPages: dto.pagination?.total_pages ?? 1,
    totalElements: dto.pagination?.total_elements ?? dataArray.length,
  };
}

export function mapThesisDetail(dto: any): ThesisDetailVM {
  return {
    urn: dto.urn,
    current_snapshot_urn: dto.current_snapshot_urn,
    title: dto.title,
    summary: dto.summary,
    rationale: dto.rationale,
    confidence: dto.confidence,
    author_urn: dto.author_urn,
    regime_urn: dto.regime_urn,
    status: dto.status,
    version: dto.version,
    assumptions: (dto.assumptions ?? []).map((a: any) => ({
      urn: a.urn,
      statement: a.statement,
      is_valid: a.is_valid,
    })),
  };
}
