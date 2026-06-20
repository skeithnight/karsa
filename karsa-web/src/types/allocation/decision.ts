/** CIO decision DTOs for proposal workflow — Sprint-06 Wave-8 */

export interface ExpectedOutcomeDTO {
  expected_return_bps: number;
  expected_drawdown_pct: number;
  expected_sharpe_ratio: number;
  expected_horizon_days: number;
  confidence_level: number;
  benchmark_urn?: string;
  regime_at_decision?: string;
  key_assumptions: Record<string, unknown>[];
  attribution_expectations: Record<string, number>;
}

export interface RiskAssessmentDTO {
  worst_case_loss_pct: number;
  concentration_risk: string;
  liquidity_risk: string;
  regime_sensitivity: string;
}

export interface ReviewHorizonDTO {
  review_date: string;
  review_criteria: string;
  auto_expire: boolean;
}

export interface VoteDTO {
  voter_id: string;
  vote_type: string;
}

export interface ProposalApproveRequest {
  proposal_id: string;
  decision_id: string;
  action_type: "APPROVE_ALLOCATION";
  votes: VoteDTO[];
  expected_outcome: ExpectedOutcomeDTO;
  risk_assessment: RiskAssessmentDTO;
  review_horizon: ReviewHorizonDTO;
}

export interface ProposalRejectRequest {
  proposal_id: string;
  decision_id: string;
  action_type: "REJECT_ALLOCATION";
  rejection_reason: string;
  votes: VoteDTO[];
}

export interface ProposalModifyRequest {
  proposal_id: string;
  decision_id: string;
  action_type: "OVERRIDE";
  modified_weights: Record<string, number>;
  modification_reason: string;
  votes: VoteDTO[];
  expected_outcome: ExpectedOutcomeDTO;
  risk_assessment: RiskAssessmentDTO;
  review_horizon: ReviewHorizonDTO;
}

export interface DecisionResponseDTO {
  decision_id: string;
  decision_journal_ref: string;
  cryptographic_signature: string;
  status: string;
}
