/** Allocation view models — Sprint-06 Wave-8 */

export interface ProposedWeightVM {
  workerUrn: string;
  proposedWeight: string;
  rankingScore: string;
  eligibilityStatus: string;
  rationale: string;
}

export interface ProposalVM {
  proposalId: string;
  policyId: string;
  totalCapital: string;
  workerCount: number;
  status: string;
  generatedAt: string;
}

export interface ProposalDetailVM {
  proposalId: string;
  policyId: string;
  journalRef: string;
  proposedWeights: ProposedWeightVM[];
  totalCapital: string;
  proposalRationale: string;
  portfolioContext: {
    currentGrossExposure: string;
    projectedGrossExposure: string;
    cashAllocationPct: string;
    concentrationImpact: string;
    alternativesConsidered: string[];
  };
  policySnapshot: {
    policyId: string;
    policyVersion: number;
    activeRules: string[];
  };
  contextHash: string;
  generatedAt: string;
  status: string;
  decisionId?: string;
  decidedAt?: string;
  decidedBy?: string;
}

export interface ProposalDecisionVM {
  decisionId: string;
  journalRef: string;
  signature: string;
  status: string;
}
