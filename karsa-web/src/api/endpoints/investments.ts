import { ApiClient } from "../client";

/** Command result from investment workflow */
export interface CommandResultDTO {
  success: boolean;
  message: string;
  request_id: string | null;
  data: Record<string, unknown> | null;
}

/** Decision detail from investment workflow */
export interface DecisionDetailDTO {
  decision_id: string;
  capability_family_id: string;
  ticker: string;
  decision_date: string;
  state: string;
  analyst_count: number;
  debate_count: number;
  has_memo: boolean;
  conviction_level: string | null;
  memo_decision: string | null;
  entry_price: number | null;
  exit_target: number | null;
  proposed_by: string;
  created_at: string;
}

export const InvestmentsApi = {
  approveDecision: (decisionId: string): Promise<CommandResultDTO> => {
    return ApiClient.fetch<CommandResultDTO>(
      `/investments/decisions/${decisionId}/approve`,
      { method: "POST" }
    );
  },

  rejectDecision: (decisionId: string): Promise<CommandResultDTO> => {
    return ApiClient.fetch<CommandResultDTO>(
      `/investments/decisions/${decisionId}/reject`,
      { method: "POST" }
    );
  },

  listDecisions: (ticker?: string): Promise<DecisionDetailDTO[]> => {
    const params = ticker ? `?ticker=${encodeURIComponent(ticker)}` : "";
    return ApiClient.fetch<DecisionDetailDTO[]>(`/investments/decisions${params}`);
  },

  getDecision: (decisionId: string): Promise<DecisionDetailDTO> => {
    return ApiClient.fetch<DecisionDetailDTO>(`/investments/decisions/${decisionId}`);
  },
};
