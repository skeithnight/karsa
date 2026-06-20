/** Allocation React Query hooks — Sprint-06 Wave-8 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  generateProposal,
  listProposals,
  getProposal,
  submitProposalDecision,
} from "../../api/endpoints/allocation";
import type { ProposalCreateRequest } from "../../types/allocation/proposal";
import type {
  ProposalApproveRequest,
  ProposalRejectRequest,
  ProposalModifyRequest,
} from "../../types/allocation/decision";

const QUERY_KEYS = {
  proposals: ["allocation", "proposals"] as const,
  proposal: (id: string) => ["allocation", "proposals", id] as const,
};

export function useListProposals(params?: {
  status?: string;
  page?: number;
  size?: number;
}) {
  return useQuery({
    queryKey: [...QUERY_KEYS.proposals, params],
    queryFn: () => listProposals(params),
  });
}

export function useProposalDetail(proposalId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.proposal(proposalId),
    queryFn: () => getProposal(proposalId),
    enabled: !!proposalId,
  });
}

export function useGenerateProposal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: ProposalCreateRequest) => generateProposal(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.proposals });
    },
  });
}

export function useProposalDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      request: ProposalApproveRequest | ProposalRejectRequest | ProposalModifyRequest
    ) => submitProposalDecision(request),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.proposals });
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.proposal(variables.proposal_id),
      });
    },
  });
}
