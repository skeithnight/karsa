/** Allocation DTO → VM mappers — Sprint-06 Wave-8 */
import type {
  ProposalDTO,
  ProposalListItemDTO,
  ProposalDetailDTO,
} from "../../../types/allocation/proposal";
import type { DecisionResponseDTO } from "../../../types/allocation/decision";
import type {
  ProposalVM,
  ProposalDetailVM,
  ProposedWeightVM,
  ProposalDecisionVM,
} from "../types/viewmodels";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number): string {
  return value.toFixed(4);
}

export function mapProposalListItem(dto: ProposalListItemDTO): ProposalVM {
  return {
    proposalId: dto.proposal_id,
    policyId: dto.policy_id,
    totalCapital: formatCurrency(dto.total_capital),
    workerCount: dto.worker_count,
    status: dto.status || "PENDING",
    generatedAt: new Date(dto.generated_at).toLocaleString(),
  };
}

export function mapProposalList(items: ProposalListItemDTO[]): ProposalVM[] {
  return items.map(mapProposalListItem);
}

export function mapProposalDetail(dto: ProposalDetailDTO): ProposalDetailVM {
  const weights: ProposedWeightVM[] = Object.values(dto.proposed_weights).map(
    (w) => ({
      workerUrn: w.worker_urn,
      proposedWeight: formatPercent(w.proposed_weight),
      rankingScore: formatScore(w.ranking_score),
      eligibilityStatus: w.eligibility_status,
      rationale: w.rationale,
    })
  );

  return {
    proposalId: dto.proposal_id,
    policyId: dto.policy_id,
    journalRef: dto.journal_ref,
    proposedWeights: weights,
    totalCapital: formatCurrency(dto.total_capital),
    proposalRationale: dto.proposal_rationale,
    portfolioContext: {
      currentGrossExposure: formatPercent(
        dto.portfolio_context.current_gross_exposure
      ),
      projectedGrossExposure: formatPercent(
        dto.portfolio_context.projected_gross_exposure
      ),
      cashAllocationPct: formatPercent(
        dto.portfolio_context.cash_allocation_pct
      ),
      concentrationImpact: dto.portfolio_context.concentration_impact,
      alternativesConsidered: dto.portfolio_context.alternatives_considered,
    },
    policySnapshot: {
      policyId: dto.policy_snapshot.policy_id,
      policyVersion: dto.policy_snapshot.policy_version,
      activeRules: dto.policy_snapshot.active_rules,
    },
    contextHash: dto.context_hash,
    generatedAt: new Date(dto.generated_at).toLocaleString(),
    status: dto.status || "PENDING",
    decisionId: dto.decision_id,
    decidedAt: dto.decided_at
      ? new Date(dto.decided_at).toLocaleString()
      : undefined,
    decidedBy: dto.decided_by,
  };
}

export function mapDecisionResponse(dto: DecisionResponseDTO): ProposalDecisionVM {
  return {
    decisionId: dto.decision_id,
    journalRef: dto.decision_journal_ref,
    signature: dto.cryptographic_signature,
    status: dto.status,
  };
}
