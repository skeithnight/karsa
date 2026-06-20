/** Allocation API client — Sprint-06 Wave-8 */
import { ApiClient } from "../client";
import type {
  ProposalCreateRequest,
  ProposalDTO,
  ProposalListResponseDTO,
  ProposalDetailDTO,
} from "../../types/allocation/proposal";
import type {
  ProposalApproveRequest,
  ProposalRejectRequest,
  ProposalModifyRequest,
  DecisionResponseDTO,
} from "../../types/allocation/decision";

const BASE = "/allocation";

export async function generateProposal(
  request: ProposalCreateRequest
): Promise<ProposalDTO> {
  return ApiClient.fetch<ProposalDTO>(`${BASE}/proposals`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function listProposals(params?: {
  status?: string;
  page?: number;
  size?: number;
}): Promise<ProposalListResponseDTO> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.size) searchParams.set("size", String(params.size));
  const qs = searchParams.toString();
  return ApiClient.fetch<ProposalListResponseDTO>(
    `${BASE}/proposals${qs ? `?${qs}` : ""}`
  );
}

export async function getProposal(
  proposalId: string
): Promise<ProposalDetailDTO> {
  return ApiClient.fetch<ProposalDetailDTO>(
    `${BASE}/proposals/${encodeURIComponent(proposalId)}`
  );
}

export async function submitProposalDecision(
  request: ProposalApproveRequest | ProposalRejectRequest | ProposalModifyRequest
): Promise<DecisionResponseDTO> {
  return ApiClient.fetch<DecisionResponseDTO>("/cio/decisions/proposal", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
