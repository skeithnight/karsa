"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "../../components/shared/PageHeader";
import { MetricCard } from "../../components/shared/MetricCard";
import { LoadingSkeleton } from "../../components/shared/LoadingSkeleton";
import { EmptyState } from "../../components/shared/EmptyState";
import { ErrorState } from "../../components/shared/ErrorState";
import { useListProposals } from "../../hooks/allocation";
import { mapProposalList } from "../../features/allocation/utils/mappers";

export default function ProposalsPage() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useListProposals();

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader title="Allocation Proposals" />
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader title="Allocation Proposals" />
        <ErrorState
          message="Failed to load proposals."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const proposals = data?.data || [];
  const viewModels = mapProposalList(proposals);

  const totalProposals = viewModels.length;
  const pendingProposals = viewModels.filter(
    (p) => p.status === "PENDING"
  ).length;
  const approvedProposals = viewModels.filter(
    (p) => p.status === "APPROVED"
  ).length;

  if (totalProposals === 0) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader title="Allocation Proposals" />
        <EmptyState
          message="No allocation proposals available."
          actionLabel="Generate Proposal"
          onAction={() => {
            /* TODO: open generate dialog */
          }}
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader title="Allocation Proposals" />

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Total Proposals" metric={String(totalProposals)} />
        <MetricCard
          title="Pending Proposals"
          metric={String(pendingProposals)}
          statusIndicator={pendingProposals > 0 ? "neutral" : "positive"}
        />
        <MetricCard
          title="Approved Proposals"
          metric={String(approvedProposals)}
          statusIndicator="positive"
        />
      </div>

      {/* Proposal Table */}
      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left text-sm font-medium">Proposal ID</th>
              <th className="p-3 text-left text-sm font-medium">Policy</th>
              <th className="p-3 text-right text-sm font-medium">Workers</th>
              <th className="p-3 text-right text-sm font-medium">Capital</th>
              <th className="p-3 text-center text-sm font-medium">Status</th>
              <th className="p-3 text-right text-sm font-medium">Generated</th>
            </tr>
          </thead>
          <tbody>
            {viewModels.map((proposal) => (
              <tr
                key={proposal.proposalId}
                className="border-b hover:bg-muted/50 cursor-pointer"
                onClick={() =>
                  router.push(`/proposals/${encodeURIComponent(proposal.proposalId)}`)
                }
              >
                <td className="p-3 text-sm font-mono">
                  {proposal.proposalId.split(":").pop()}
                </td>
                <td className="p-3 text-sm">{proposal.policyId}</td>
                <td className="p-3 text-sm text-right">{proposal.workerCount}</td>
                <td className="p-3 text-sm text-right font-medium">
                  {proposal.totalCapital}
                </td>
                <td className="p-3 text-sm text-center">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      proposal.status === "APPROVED"
                        ? "bg-green-100 text-green-800"
                        : proposal.status === "REJECTED"
                        ? "bg-red-100 text-red-800"
                        : proposal.status === "MODIFIED"
                        ? "bg-yellow-100 text-yellow-800"
                        : proposal.status === "EXPIRED"
                        ? "bg-gray-100 text-gray-800"
                        : "bg-blue-100 text-blue-800"
                    }`}
                  >
                    {proposal.status}
                  </span>
                </td>
                <td className="p-3 text-sm text-right text-muted-foreground">
                  {proposal.generatedAt}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
