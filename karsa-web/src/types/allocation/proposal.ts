/** Allocation proposal DTOs — Sprint-06 Wave-8 */

export interface RiskBudgetDTO {
  max_volatility: number;
  max_drawdown: number;
  max_exposure: number;
}

export interface ProposedWeightDTO {
  worker_urn: string;
  proposed_weight: number;
  ranking_score: number;
  eligibility_status: string;
  rationale: string;
  risk_budget: RiskBudgetDTO;
}

export interface PolicySnapshotDTO {
  policy_id: string;
  policy_version: number;
  policy_hash: string;
  active_rules: string[];
}

export interface PortfolioContextDTO {
  current_gross_exposure: number;
  current_net_exposure: number;
  current_cash_ratio: number;
  current_concentration: number;
  projected_gross_exposure: number;
  projected_net_exposure: number;
  projected_cash_ratio: number;
  projected_concentration: number;
  cash_allocation_pct: number;
  concentration_impact: string;
  alternatives_considered: string[];
}

export interface ProposalDTO {
  proposal_id: string;
  policy_id: string;
  journal_ref: string;
  proposed_weights: Record<string, ProposedWeightDTO>;
  total_capital: number;
  proposal_rationale: string;
  portfolio_context: PortfolioContextDTO;
  policy_snapshot: PolicySnapshotDTO;
  context_hash: string;
  generated_at: string;
  status?: string;
}

export interface ProposalListItemDTO {
  proposal_id: string;
  policy_id: string;
  total_capital: number;
  worker_count: number;
  status?: string;
  generated_at: string;
}

export interface ProposalListResponseDTO {
  data: ProposalListItemDTO[];
  pagination: {
    page: number;
    size: number;
    total_items: number;
  };
}

export interface ProposalDetailDTO extends ProposalDTO {
  decision_id?: string;
  decided_at?: string;
  decided_by?: string;
}

export interface ProposalCreateRequest {
  total_capital: number;
  policy_id?: string;
}
