export interface InvestmentOversightVM {
  id: string;
  thesisUrn: string;
  failureReason: string;
  policyOverridesRaw: boolean;
  policyOverridesDisplay: string;
  timestampRaw: string;
  timestampDisplay: string;
}

export interface ListInvestmentOversightVM {
  data: InvestmentOversightVM[];
  nextCursor?: string;
}
