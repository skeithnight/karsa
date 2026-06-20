"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import type { ProposalDetailVM } from "../../../../features/allocation/types/viewmodels";
import { ApprovalForm } from "./ApprovalForm";

interface ProposalDetailViewProps {
  proposal: ProposalDetailVM;
  onDecisionSuccess: () => void;
}

export function ProposalDetailView({ proposal, onDecisionSuccess }: ProposalDetailViewProps) {
  const [showForm, setShowForm] = useState(false);
  const isPending = proposal.status === "PENDING";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${proposal.status === "APPROVED" ? "bg-green-100 text-green-800" : proposal.status === "REJECTED" ? "bg-red-100 text-red-800" : proposal.status === "MODIFIED" ? "bg-yellow-100 text-yellow-800" : "bg-blue-100 text-blue-800"}`}>{proposal.status}</span>
        <span className="text-sm text-muted-foreground">Generated: {proposal.generatedAt}</span>
      </div>

      <Card>
        <CardHeader><CardTitle>Proposal Summary</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><div className="text-sm text-muted-foreground">Proposal ID</div><div className="text-sm font-mono">{proposal.proposalId}</div></div>
          <div><div className="text-sm text-muted-foreground">Policy</div><div className="text-sm">{proposal.policyId}</div></div>
          <div><div className="text-sm text-muted-foreground">Total Capital</div><div className="text-sm font-medium">{proposal.totalCapital}</div></div>
          <div><div className="text-sm text-muted-foreground">Journal Ref</div><div className="text-sm font-mono truncate">{proposal.journalRef}</div></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Proposed Weights</CardTitle></CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <table className="w-full">
              <thead><tr className="border-b bg-muted/50">
                <th className="p-3 text-left text-sm font-medium">Worker</th>
                <th className="p-3 text-right text-sm font-medium">Weight</th>
                <th className="p-3 text-right text-sm font-medium">Score</th>
                <th className="p-3 text-center text-sm font-medium">Eligibility</th>
                <th className="p-3 text-left text-sm font-medium">Rationale</th>
              </tr></thead>
              <tbody>
                {proposal.proposedWeights.map(w => (
                  <tr key={w.workerUrn} className="border-b">
                    <td className="p-3 text-sm font-mono">{w.workerUrn}</td>
                    <td className="p-3 text-sm text-right font-medium">{w.proposedWeight}</td>
                    <td className="p-3 text-sm text-right">{w.rankingScore}</td>
                    <td className="p-3 text-sm text-center"><span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${w.eligibilityStatus === "ALLOCATABLE" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>{w.eligibilityStatus}</span></td>
                    <td className="p-3 text-sm text-muted-foreground">{w.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Portfolio Context</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><div className="text-sm text-muted-foreground">Current Exposure</div><div className="text-sm">{proposal.portfolioContext.currentGrossExposure}</div></div>
          <div><div className="text-sm text-muted-foreground">Projected Exposure</div><div className="text-sm font-medium">{proposal.portfolioContext.projectedGrossExposure}</div></div>
          <div><div className="text-sm text-muted-foreground">Cash Allocation</div><div className="text-sm">{proposal.portfolioContext.cashAllocationPct}</div></div>
          <div><div className="text-sm text-muted-foreground">Concentration</div><div className="text-sm"><span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${proposal.portfolioContext.concentrationImpact === "LOW" ? "bg-green-100 text-green-800" : proposal.portfolioContext.concentrationImpact === "MEDIUM" ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800"}`}>{proposal.portfolioContext.concentrationImpact}</span></div></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Policy Snapshot</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div><div className="text-sm text-muted-foreground">Policy ID</div><div className="text-sm">{proposal.policySnapshot.policyId}</div></div>
            <div><div className="text-sm text-muted-foreground">Version</div><div className="text-sm">{proposal.policySnapshot.policyVersion}</div></div>
          </div>
          <div><div className="text-sm text-muted-foreground mb-1">Active Rules</div><ul className="list-disc list-inside space-y-1">{proposal.policySnapshot.activeRules.map((r, i) => <li key={i} className="text-sm">{r}</li>)}</ul></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Rationale</CardTitle></CardHeader>
        <CardContent><p className="text-sm">{proposal.proposalRationale}</p></CardContent>
      </Card>

      {!isPending && proposal.decisionId && (
        <Card>
          <CardHeader><CardTitle>Decision</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div><div className="text-sm text-muted-foreground">Decision ID</div><div className="text-sm font-mono">{proposal.decisionId}</div></div>
            <div><div className="text-sm text-muted-foreground">Decided By</div><div className="text-sm">{proposal.decidedBy || "—"}</div></div>
            <div><div className="text-sm text-muted-foreground">Decided At</div><div className="text-sm">{proposal.decidedAt || "—"}</div></div>
          </CardContent>
        </Card>
      )}

      {isPending && (
        <Card>
          <CardHeader><CardTitle>Actions</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Button onClick={() => setShowForm(true)}>Approve</Button>
              <Button variant="outline" onClick={() => setShowForm(true)}>Reject</Button>
              <Button variant="outline" onClick={() => setShowForm(true)}>Modify</Button>
            </div>
            {showForm && <ApprovalForm proposalId={proposal.proposalId} onCancel={() => setShowForm(false)} onSuccess={() => { setShowForm(false); onDecisionSuccess(); }} />}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
