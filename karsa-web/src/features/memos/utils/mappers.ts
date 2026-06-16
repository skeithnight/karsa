import { DecisionMemoDTO } from "../../../types/memos/memo.dto";
import { ListMemosResponseDTO } from "../../../types/memos/list-memos-response.dto";
import { formatDate } from "../../../lib/formatters/date";
import { InvestmentMemoVM, ListInvestmentMemosVM } from "../types/viewmodels";

export function mapInvestmentMemo(dto: DecisionMemoDTO): InvestmentMemoVM {
  return {
    decisionUrn: dto.decision_urn,
    thesisUrn: dto.thesis_urn,
    intent: dto.intent,
    pepSignature: dto.pep_signature,
    timestampRaw: dto.timestamp,
    timestampDisplay: formatDate(dto.timestamp, "short"),
  };
}

export function mapListInvestmentMemos(dto: ListMemosResponseDTO): ListInvestmentMemosVM {
  return {
    data: (dto.data ?? []).map(mapInvestmentMemo),
    totalPages: dto.pagination?.total_pages ?? 1,
    totalElements: dto.pagination?.total_elements ?? 0,
  };
}
