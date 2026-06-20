import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { generateProposal, listProposals, getProposal, submitProposalDecision } from "../../api/endpoints/allocation";
import type { ProposalCreateRequest } from "../../types/allocation/proposal";
import type { ProposalApproveRequest, ProposalRejectRequest, ProposalModifyRequest } from "../../types/allocation/decision";

const QK = { proposals: ["allocation", "proposals"] as const, proposal: (id: string) => ["allocation", "proposals", id] as const };

export function useListProposals(params?: { status?: string; page?: number; size?: number }) {
  return useQuery({ queryKey: [...QK.proposals, params], queryFn: () => listProposals(params) });
}

export function useProposalDetail(proposalId: string) {
  return useQuery({ queryKey: QK.proposal(proposalId), queryFn: () => getProposal(proposalId), enabled: !!proposalId });
}

export function useGenerateProposal() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (r: ProposalCreateRequest) => generateProposal(r), onSuccess: () => qc.invalidateQueries({ queryKey: QK.proposals }) });
}

export function useProposalDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (r: ProposalApproveRequest | ProposalRejectRequest | ProposalModifyRequest) => submitProposalDecision(r),
    onSuccess: (_d, v) => { qc.invalidateQueries({ queryKey: QK.proposals }); qc.invalidateQueries({ queryKey: QK.proposal(v.proposal_id) }); },
  });
}
