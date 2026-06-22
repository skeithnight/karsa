"use client";

import React, { useState } from "react";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { useProposalDecision } from "../../../../hooks/allocation";
import { useNotifications } from "../../../../components/shared/NotificationCenter";

interface ApprovalFormProps {
  proposalId: string;
  onCancel: () => void;
  onSuccess: () => void;
}

type ActionType = "APPROVE_ALLOCATION" | "REJECT_ALLOCATION" | "OVERRIDE";

export function ApprovalForm({
  proposalId,
  onCancel,
  onSuccess,
}: ApprovalFormProps) {
  const decisionMutation = useProposalDecision();
  const { addNotification } = useNotifications();

  const [actionType, setActionType] = useState<ActionType>("APPROVE_ALLOCATION");

  // Expected Outcome
  const [expectedReturnBps, setExpectedReturnBps] = useState("50");
  const [expectedDrawdownPct, setExpectedDrawdownPct] = useState("5");
  const [expectedSharpeRatio, setExpectedSharpeRatio] = useState("1.5");
  const [expectedHorizonDays, setExpectedHorizonDays] = useState("30");
  const [confidenceLevel, setConfidenceLevel] = useState("0.7");

  // Risk Assessment
  const [worstCaseLossPct, setWorstCaseLossPct] = useState("8");
  const [concentrationRisk, setConcentrationRisk] = useState("LOW");
  const [liquidityRisk, setLiquidityRisk] = useState("LOW");
  const [regimeSensitivity, setRegimeSensitivity] = useState("MEDIUM");

  // Review Horizon
  const [reviewDate, setReviewDate] = useState("2026-07-20");
  const [reviewCriteria, setReviewCriteria] = useState(
    "Evaluate if cumulative alpha exceeds target."
  );

  // Reject/Modify
  const [rejectionReason, setRejectionReason] = useState("");
  const [modificationReason, setModificationReason] = useState("");

  const handleSubmit = () => {
    const decisionId = `dec-${Date.now()}`;
    const votes = [{ voter_id: "cio-1", vote_type: "APPROVE" }];

    const baseExpectedOutcome = {
      expected_return_bps: parseFloat(expectedReturnBps),
      expected_drawdown_pct: parseFloat(expectedDrawdownPct),
      expected_sharpe_ratio: parseFloat(expectedSharpeRatio),
      expected_horizon_days: parseInt(expectedHorizonDays),
      confidence_level: parseFloat(confidenceLevel),
      key_assumptions: [],
      attribution_expectations: {},
    };

    const baseRiskAssessment = {
      worst_case_loss_pct: parseFloat(worstCaseLossPct),
      concentration_risk: concentrationRisk,
      liquidity_risk: liquidityRisk,
      regime_sensitivity: regimeSensitivity,
    };

    const baseReviewHorizon = {
      review_date: `${reviewDate}T00:00:00Z`,
      review_criteria: reviewCriteria,
      auto_expire: false,
    };

    const handleSuccess = () => {
      addNotification({
        type: "success",
        title: `Proposal ${actionType === "APPROVE_ALLOCATION" ? "Approved" : actionType === "REJECT_ALLOCATION" ? "Rejected" : "Modified"}`,
        message: `Proposal ${proposalId} has been ${actionType === "APPROVE_ALLOCATION" ? "approved" : actionType === "REJECT_ALLOCATION" ? "rejected" : "modified"} successfully.`,
      });
      onSuccess();
    };

    if (actionType === "APPROVE_ALLOCATION") {
      decisionMutation.mutate(
        {
          proposal_id: proposalId,
          decision_id: decisionId,
          action_type: "APPROVE_ALLOCATION",
          votes,
          expected_outcome: baseExpectedOutcome,
          risk_assessment: baseRiskAssessment,
          review_horizon: baseReviewHorizon,
        },
        { onSuccess: handleSuccess }
      );
    } else if (actionType === "REJECT_ALLOCATION") {
      decisionMutation.mutate(
        {
          proposal_id: proposalId,
          decision_id: decisionId,
          action_type: "REJECT_ALLOCATION",
          rejection_reason: rejectionReason || "Rejected by CIO.",
          votes: [{ voter_id: "cio-1", vote_type: "REJECT" }],
        },
        { onSuccess: handleSuccess }
      );
    } else if (actionType === "OVERRIDE") {
      decisionMutation.mutate(
        {
          proposal_id: proposalId,
          decision_id: decisionId,
          action_type: "OVERRIDE",
          modified_weights: {},
          modification_reason: modificationReason || "Modified by CIO.",
          votes,
          expected_outcome: baseExpectedOutcome,
          risk_assessment: baseRiskAssessment,
          review_horizon: baseReviewHorizon,
        },
        { onSuccess: handleSuccess }
      );
    }
  };

  const riskLevels = ["LOW", "MEDIUM", "HIGH"];

  return (
    <div className="space-y-4 border-t pt-4">
      {/* Action Type Selector */}
      <div className="flex gap-2">
        <Button
          variant={actionType === "APPROVE_ALLOCATION" ? "default" : "outline"}
          onClick={() => setActionType("APPROVE_ALLOCATION")}
          size="sm"
        >
          Approve
        </Button>
        <Button
          variant={actionType === "REJECT_ALLOCATION" ? "default" : "outline"}
          onClick={() => setActionType("REJECT_ALLOCATION")}
          size="sm"
        >
          Reject
        </Button>
        <Button
          variant={actionType === "OVERRIDE" ? "default" : "outline"}
          onClick={() => setActionType("OVERRIDE")}
          size="sm"
        >
          Modify
        </Button>
      </div>

      {/* Expected Outcome (for Approve/Modify) */}
      {(actionType === "APPROVE_ALLOCATION" || actionType === "OVERRIDE") && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Expected Outcome</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-muted-foreground">
                Expected Return (bps)
              </label>
              <Input
                type="number"
                value={expectedReturnBps}
                onChange={(e) => setExpectedReturnBps(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Expected Drawdown (%)
              </label>
              <Input
                type="number"
                value={expectedDrawdownPct}
                onChange={(e) => setExpectedDrawdownPct(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Expected Sharpe
              </label>
              <Input
                type="number"
                value={expectedSharpeRatio}
                onChange={(e) => setExpectedSharpeRatio(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Horizon (days)
              </label>
              <Input
                type="number"
                value={expectedHorizonDays}
                onChange={(e) => setExpectedHorizonDays(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Confidence (0-1)
              </label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={confidenceLevel}
                onChange={(e) => setConfidenceLevel(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Risk Assessment (for Approve/Modify) */}
      {(actionType === "APPROVE_ALLOCATION" || actionType === "OVERRIDE") && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Risk Assessment</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-muted-foreground">
                Worst Case Loss (%)
              </label>
              <Input
                type="number"
                value={worstCaseLossPct}
                onChange={(e) => setWorstCaseLossPct(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Concentration Risk
              </label>
              <select
                className="w-full p-2 border rounded text-sm"
                value={concentrationRisk}
                onChange={(e) => setConcentrationRisk(e.target.value)}
              >
                {riskLevels.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Liquidity Risk
              </label>
              <select
                className="w-full p-2 border rounded text-sm"
                value={liquidityRisk}
                onChange={(e) => setLiquidityRisk(e.target.value)}
              >
                {riskLevels.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Regime Sensitivity
              </label>
              <select
                className="w-full p-2 border rounded text-sm"
                value={regimeSensitivity}
                onChange={(e) => setRegimeSensitivity(e.target.value)}
              >
                {riskLevels.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Review Horizon (for Approve/Modify) */}
      {(actionType === "APPROVE_ALLOCATION" || actionType === "OVERRIDE") && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Review Horizon</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground">
                Review Date
              </label>
              <Input
                type="date"
                value={reviewDate}
                onChange={(e) => setReviewDate(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Review Criteria
              </label>
              <Textarea
                value={reviewCriteria}
                onChange={(e) => setReviewCriteria(e.target.value)}
                rows={2}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rejection Reason */}
      {actionType === "REJECT_ALLOCATION" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Rejection Reason</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Provide reason for rejection..."
              rows={3}
            />
          </CardContent>
        </Card>
      )}

      {/* Modification Reason */}
      {actionType === "OVERRIDE" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Modification Reason</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={modificationReason}
              onChange={(e) => setModificationReason(e.target.value)}
              placeholder="Provide reason for modification..."
              rows={3}
            />
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {decisionMutation.isError && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded">
          {decisionMutation.error?.message || "Decision submission failed."}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button onClick={handleSubmit} disabled={decisionMutation.isPending}>
          {decisionMutation.isPending
            ? "Submitting..."
            : actionType === "APPROVE_ALLOCATION"
            ? "Approve Proposal"
            : actionType === "REJECT_ALLOCATION"
            ? "Reject Proposal"
            : "Submit Modification"}
        </Button>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
