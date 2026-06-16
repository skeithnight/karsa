export interface ThesisDTO {
  thesis_urn: string;
  ticker: string;
  direction: "LONG" | "SHORT";
  state: "INITIATED" | "ACTIVE" | "INVALIDATED" | "EXPIRED";
  conviction_score: number;
  expected_horizon_days: number;
}
