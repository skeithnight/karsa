import { PostMortemDTO } from "../../../types/governance/post-mortem.dto";
import { ListPostMortemsResponseDTO } from "../../../types/governance/list-post-mortems-response.dto";
import { formatDate } from "../../../lib/formatters/date";
import { InvestmentOversightVM, ListInvestmentOversightVM } from "../types/viewmodels";

export function mapInvestmentOversight(dto: PostMortemDTO): InvestmentOversightVM {
  return {
    id: dto.id,
    thesisUrn: dto.thesis_urn,
    failureReason: dto.failure_reason,
    policyOverridesRaw: dto.policy_overrides,
    policyOverridesDisplay: dto.policy_overrides ? "Policy Override" : "Standard",
    timestampRaw: dto.timestamp,
    timestampDisplay: formatDate(dto.timestamp, "short"),
  };
}

export function mapListInvestmentOversight(dto: ListPostMortemsResponseDTO): ListInvestmentOversightVM {
  return {
    data: (dto.data ?? []).map(mapInvestmentOversight),
    nextCursor: dto.next_cursor,
  };
}
