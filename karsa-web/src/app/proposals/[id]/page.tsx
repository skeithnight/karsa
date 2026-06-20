"use client";

import React from "react";
import { useParams } from "next/navigation";
import { PageHeader } from "../../../components/shared/PageHeader";
import { LoadingSkeleton } from "../../../components/shared/LoadingSkeleton";
import { ErrorState } from "../../../components/shared/ErrorState";
import { useProposalDetail } from "../../../hooks/allocation";
import { mapProposalDetail } from "../../../features/allocation/utils/mappers";
import { ProposalDetailView } from "./components/ProposalDetailView";

export default function ProposalDetailPage() {
  const params = useParams();
  const proposalId = params.id as string;

  const { data, isLoading, error, refetch } = useProposalDetail(proposalId);

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader title="Proposal Detail" />
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader title="Proposal Detail" />
        <ErrorState
          message="Failed to load proposal."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader title="Proposal Detail" />
        <ErrorState message="Proposal not found." />
      </div>
    );
  }

  const viewModel = mapProposalDetail(data);

  return (
    <div className="p-6 space-y-6">
      <PageHeader title={`Proposal ${viewModel.proposalId.split(":").pop()}`} />
      <ProposalDetailView proposal={viewModel} onDecisionSuccess={() => refetch()} />
    </div>
  );
}
