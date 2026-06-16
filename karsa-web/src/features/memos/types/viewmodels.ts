export interface InvestmentMemoVM {
  decisionUrn: string;
  thesisUrn: string;
  intent: string;
  pepSignature: string;
  timestampRaw: string;
  timestampDisplay: string;
}

export interface ListInvestmentMemosVM {
  data: InvestmentMemoVM[];
  totalPages: number;
  totalElements: number;
}
