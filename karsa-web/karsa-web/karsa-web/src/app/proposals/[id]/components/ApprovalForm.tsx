"use client";

import React, { useState } from "react";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { useProposalDecision } from "../../../../hooks/allocation";

interface ApprovalFormProps {
  proposalId: string;
  onCancel: () => void;
  onSuccess: () => void;
}

type ActionType = "APPROVE_ALLOCATION" | "REJECT_ALLOCATION" | "OVERRIDE";

export function ApprovalForm({ proposalId, onCancel, onSuccess }: ApprovalFormProps) {
  const mutation = useProposalDecision();
  const [action, setAction] = useState<ActionType>("APPROVE_ALLOCATION");
  const [returnBps, setReturnBps] = useState("50");
  const [drawdownPct, setDrawdownPct] = useState("5");
  const [sharpe, setSharpe] = useState("1.5");
  const [horizon, setHorizon] = useState("30");
  const [confidence, setConfidence] = useState("0.7");
  const [worstLoss, setWorstLoss] = useState("8");
  const [concRisk, setConcRisk] = useState("LOW");
  const [liqRisk, setLiqRisk] = useState("LOW");
  const [regimeSens, setRegimeSens] = useState("MEDIUM");
  const [reviewDate, setReviewDate] = useState("2026-07-20");
  const [reviewCriteria, setReviewCriteria] = useState("Evaluate if cumulative alpha exceeds target.");
  const [rejectReason, setRejectReason] = useState("");
  const [modifyReason, setModifyReason] = useState("");

  const handleSubmit = () => {
    const id = `dec-${Date.now()}`;
    const votes = [{ voter_id: "cio-1", vote_type: "APPROVE" }];
    const eo = { expected_return_bps: +returnBps, expected_drawdown_pct: +drawdownPct, expected_sharpe_ratio: +sharpe, expected_horizon_days: +horizon, confidence_level: +confidence, key_assumptions: [], attribution_expectations: {} };
    const ra = { worst_case_loss_pct: +worstLoss, concentration_risk: concRisk, liquidity_risk: liqRisk, regime_sensitivity: regimeSens };
    const rh = { review_date: `${reviewDate}T00:00:00Z`, review_criteria: reviewCriteria, auto_expire: false };

    if (action === "APPROVE_ALLOCATION") mutation.mutate({ proposal_id: proposalId, decision_id: id, action_type: "APPROVE_ALLOCATION", votes, expected_outcome: eo, risk_assessment: ra, review_horizon: rh }, { onSuccess });
    else if (action === "REJECT_ALLOCATION") mutation.mutate({ proposal_id: proposalId, decision_id: id, action_type: "REJECT_ALLOCATION", rejection_reason: rejectReason || "Rejected by CIO.", votes: [{ voter_id: "cio-1", vote_type: "REJECT" }] }, { onSuccess });
    else mutation.mutate({ proposal_id: proposalId, decision_id: id, action_type: "OVERRIDE", modified_weights: {}, modification_reason: modifyReason || "Modified by CIO.", votes, expected_outcome: eo, risk_assessment: ra, review_horizon: rh }, { onSuccess });
  };

  const levels = ["LOW", "MEDIUM", "HIGH"];

  return (
    <div className="space-y-4 border-t pt-4">
      <div className="flex gap-2">
        <Button variant={action === "APPROVE_ALLOCATION" ? "default" : "outline"} onClick={() => setAction("APPROVE_ALLOCATION")} size="sm">Approve</Button>
        <Button variant={action === "REJECT_ALLOCATION" ? "default" : "outline"} onClick={() => setAction("REJECT_ALLOCATION")} size="sm">Reject</Button>
        <Button variant={action === "OVERRIDE" ? "default" : "outline"} onClick={() => setAction("OVERRIDE")} size="sm">Modify</Button>
      </div>

      {(action === "APPROVE_ALLOCATION" || action === "OVERRIDE") && (
        <>
          <Card>
            <CardHeader><CardTitle className="text-sm">Expected Outcome</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <div><label className="text-xs text-muted-foreground">Return (bps)</label><Input type="number" value={returnBps} onChange={e => setReturnBps(e.target.value)} /></div>
              <div><label className="text-xs text-muted-foreground">Drawdown (%)</label><Input type="number" value={drawdownPct} onChange={e => setDrawdownPct(e.target.value)} /></div>
              <div><label className="text-xs text-muted-foreground">Sharpe</label><Input type="number" value={sharpe} onChange={e => setSharpe(e.target.value)} /></div>
              <div><label className="text-xs text-muted-foreground">Horizon (days)</label><Input type="number" value={horizon} onChange={e => setHorizon(e.target.value)} /></div>
              <div><label className="text-xs text-muted-foreground">Confidence</label><Input type="number" step="0.1" min="0" max="1" value={confidence} onChange={e => setConfidence(e.target.value)} /></div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-sm">Risk Assessment</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div><label className="text-xs text-muted-foreground">Worst Loss (%)</label><Input type="number" value={worstLoss} onChange={e => setWorstLoss(e.target.value)} /></div>
              <div><label className="text-xs text-muted-foreground">Concentration</label><select className="w-full p-2 border rounded text-sm" value={concRisk} onChange={e => setConcRisk(e.target.value)}>{levels.map(l => <option key={l}>{l}</option>)}</select></div>
              <div><label className="text-xs text-muted-foreground">Liquidity</label><select className="w-full p-2 border rounded text-sm" value={liqRisk} onChange={e => setLiqRisk(e.target.value)}>{levels.map(l => <option key={l}>{l}</option>)}</select></div>
              <div><label className="text-xs text-muted-foreground">Regime</label><select className="w-full p-2 border rounded text-sm" value={regimeSens} onChange={e => setRegimeSens(e.target.value)}>{levels.map(l => <option key={l}>{l}</option>)}</select></div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-sm">Review Horizon</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div><label className="text-xs text-muted-foreground">Review Date</label><Input type="date" value={reviewDate} onChange={e => setReviewDate(e.target.value)} /></div>
              <div><label className="text-xs text-muted-foreground">Criteria</label><Textarea value={reviewCriteria} onChange={e => setReviewCriteria(e.target.value)} rows={2} /></div>
            </CardContent>
          </Card>
        </>
      )}

      {action === "REJECT_ALLOCATION" && (
        <Card><CardHeader><CardTitle className="text-sm">Rejection Reason</CardTitle></CardHeader><CardContent><Textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Reason for rejection..." rows={3} /></CardContent></Card>
      )}

      {action === "OVERRIDE" && (
        <Card><CardHeader><CardTitle className="text-sm">Modification Reason</CardTitle></CardHeader><CardContent><Textarea value={modifyReason} onChange={e => setModifyReason(e.target.value)} placeholder="Reason for modification..." rows={3} /></CardContent></Card>
      )}

      {mutation.isError && <div className="text-sm text-red-600 bg-red-50 p-3 rounded">{mutation.error?.message || "Decision failed."}</div>}

      <div className="flex gap-3">
        <Button onClick={handleSubmit} disabled={mutation.isPending}>{mutation.isPending ? "Submitting..." : action === "APPROVE_ALLOCATION" ? "Approve" : action === "REJECT_ALLOCATION" ? "Reject" : "Submit Modification"}</Button>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}
