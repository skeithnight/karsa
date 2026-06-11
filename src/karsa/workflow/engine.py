from karsa.models.state import WorkflowState
from karsa.workflow.controller import StateController
from karsa.artifacts.manager import ArtifactManager
from karsa.git.manager import GitManager
from karsa.agents.product_engineer import ProductEngineerAgent
from karsa.agents.review_agent import ReviewAgent
import typer
from karsa.observability.manager import ObservabilityManager

from karsa.review.registry import IssueRegistry
from karsa.review.convergence import ReviewConvergenceEngine, ReviewParsingException


def _extract_decision_reason(review_text: str, outcome: str, metrics: dict) -> str:
    """Extract a meaningful reason from review text. Never returns empty or 'Unknown'."""
    import re
    
    # Try multiple heading patterns for reason extraction
    reason_patterns = [
        r'# (?:Rejection|Approval) Reason\n(.*?)(?:\n#|$)',
        r'## (?:Rejection|Approval) Reason\n(.*?)(?:\n#|$)',
        r'# Summary\n(.*?)(?:\n#|$)',
        r'## Summary\n(.*?)(?:\n#|$)',
    ]
    
    for pattern in reason_patterns:
        match = re.search(pattern, review_text, re.DOTALL)
        if match:
            reason = match.group(1).strip()
            if reason and reason.lower() != 'unknown':
                return reason
    
    # Synthesize reason from outcome and metrics
    blocking = metrics.get('blocking_issue_count', 0)
    non_blocking = metrics.get('non_blocking_issue_count', 0)
    resolved = metrics.get('resolved_count', 0)
    
    if outcome == "APPROVE":
        return f"All blocking issues resolved. {resolved} issues resolved total. {non_blocking} non-blocking issues remaining."
    elif outcome == "REJECT":
        return f"Review rejected: {blocking} blocking issues remain unresolved. {non_blocking} non-blocking issues. {resolved} issues resolved."
    else:
        return f"Review outcome: {outcome}. {blocking} blocking, {non_blocking} non-blocking, {resolved} resolved."


class RevisionEngine:
    def __init__(self, state_controller: StateController, artifact_manager: ArtifactManager, git_manager: GitManager, pe_agent: ProductEngineerAgent, review_agent: ReviewAgent, issue_registry: IssueRegistry, convergence_engine: ReviewConvergenceEngine, obs_manager: ObservabilityManager = None):
        self.state = state_controller
        self.artifacts = artifact_manager
        self.git = git_manager
        self.pe_agent = pe_agent
        self.review_agent = review_agent
        self.issue_registry = issue_registry
        self.convergence = convergence_engine
        self.obs = obs_manager

    def run_loop(self):
        max_cycles = 3
        cycle = 1

        while cycle <= max_cycles:
            typer.echo(f"--- Review Cycle {cycle} ---")
            
            # Update authoritative cycle tracking
            self.state.update_cycle(cycle)
            
            typer.echo("Challenging design with ReviewAgent...")
            
            active_issues = self.issue_registry.get_active_issues()
            active_issues_text = "\n\n".join([f"Issue: {i.id}\nDescription: {i.description}\nEvidence: {i.evidence}" for i in active_issues])
            
            try:
                outcome, review_text = self.review_agent.review_design(cycle, active_issues_text)
            except Exception as e:
                typer.echo(f"Critical Failure: {str(e)}")
                if "429 QUOTA" in str(e).upper() or "ALL PROVIDERS FAILED" in str(e).upper():
                    self.state.transition_to(WorkflowState.AWAITING_PROVIDER)
                    self.git.commit_state("Karsa: Workflow paused awaiting provider capacity")
                else:
                    self.state.transition_to(WorkflowState.FAILED)
                    self.git.commit_state("Karsa: Workflow FAILED due to provider failure")
                return
                
            self.artifacts.write_artifact(f"docs/reviews/REVIEW_{cycle:03d}.md", review_text) # Store history
            
            # Process review to update issues
            try:
                diagnostics = self.convergence.process_review(review_text, cycle)
            except ReviewParsingException as e:
                typer.echo(f"CRITICAL: Review parsing failure detected - failing closed: {str(e)}")
                typer.echo("Treating review as REJECT due to parsing failure. This is a safety measure.")
                diagnostics = {
                    "detected_outcome": "REJECT",
                    "extracted_new_blocking": -1,
                    "extracted_new_non_blocking": -1,
                    "parse_warnings": [f"ReviewParsingException: {str(e)}"],
                    "confidence": 0.0,
                    "issue_extraction_failed": True
                }
                outcome = "REJECT"
                metrics = self.convergence.get_metrics()
                should_approve = False
                
                # Update authoritative state
                self.state.update_decision(outcome)
                self.state.update_issues(
                    metrics["blocking_issue_count"],
                    metrics["non_blocking_issue_count"],
                    metrics["resolved_count"]
                )
                
                if self.obs:
                    self.obs.record_decision(
                        agent="ReviewAgent",
                        decision="REJECT",
                        reason=f"Review parsing failure: {str(e)}",
                        evidence="Fail-closed: parsing exception triggered safety rejection",
                        confidence=0.0,
                        provider=getattr(self.review_agent.llm, "model_name", "unknown"),
                        key_fingerprint=getattr(self.review_agent.llm, "current_key", "none")
                    )
                
                self.state.transition_to(WorkflowState.REVIEW)
                self.git.commit_state(f"Karsa: Review Cycle {cycle} - REJECT (parsing failure, fail-closed)")
                typer.echo(f"Review outcome: REJECT (parsing failure)")
                
                # Do NOT approve - continue to revision or escalation
                if cycle == max_cycles:
                    typer.echo("Max revision cycles reached without approval. Escalating to Founder.")
                    self.state.transition_to(WorkflowState.ESCALATED)
                    self.git.commit_state("Karsa: Escalated to Founder due to max revisions")
                    return
                cycle += 1
                continue

            metrics = self.convergence.get_metrics()
            should_approve = self.convergence.should_approve_safe(diagnostics)
            
            # Cross-check: if LLM said REJECT but registry says approve, force REJECT
            if outcome == "REJECT" and should_approve:
                typer.echo(f"WARNING: Registry shows 0 blocking issues but LLM outcome was REJECT. Forcing REJECT (fail-closed).")
                should_approve = False
            
            if should_approve:
                outcome = "APPROVE"
            else:
                outcome = "REJECT"

            self.state.transition_to(WorkflowState.REVIEW)
            self.git.commit_state(f"Karsa: Generated Review Cycle {cycle} - Outcome: {outcome}")
            typer.echo(f"Review outcome: {outcome}")
            
            # Update authoritative state with decision and issues
            self.state.update_decision(outcome)
            self.state.update_issues(
                metrics["blocking_issue_count"],
                metrics["non_blocking_issue_count"],
                metrics["resolved_count"]
            )
            
            if self.obs:
                import re
                reason = _extract_decision_reason(review_text, outcome, metrics)
                confidence = 1.0
                
                evidence = f"{metrics['blocking_issue_count']} blocking issues, {metrics['non_blocking_issue_count']} non-blocking."
                
                conf_match = re.search(r'# Confidence\n([0-9.]+)', review_text)
                if conf_match:
                    try:
                        confidence = float(conf_match.group(1))
                    except:
                        pass
                        
                self.obs.record_decision(
                    agent="ReviewAgent",
                    decision=outcome,
                    reason=reason,
                    evidence=evidence,
                    confidence=confidence,
                    provider=getattr(self.review_agent.llm, "model_name", "unknown"),
                    key_fingerprint=getattr(self.review_agent.llm, "current_key", "none")
                )
                
                # Assume a simple convergence score = resolved - new
                # In reality we might want a running total or delta
                new_issues_in_review = len(re.findall(r'Issue:\s*[A-Z0-9]+\nSeverity:', review_text))
                resolved_in_review = len(re.findall(r'Status:\s*RESOLVED', review_text))
                convergence_score = resolved_in_review - new_issues_in_review
                
                self.obs.metrics_tracker.record_metrics(
                    cycle=cycle,
                    blocking=metrics["blocking_issue_count"],
                    non_blocking=metrics["non_blocking_issue_count"],
                    resolved=metrics["resolved_count"],
                    new=new_issues_in_review,
                    convergence_score=convergence_score
                )

            if outcome == "APPROVE":
                self.state.transition_to(WorkflowState.APPROVED)
                self.git.commit_state("Karsa: Design Approved")
                typer.echo("Workflow APPROVED. Stopping.")
                return

            if cycle > 1 and convergence_score < 0:
                typer.echo("Review diverging (convergence score < 0). Escalating to Founder to prevent infinite review loop.")
                self.state.transition_to(WorkflowState.ESCALATED)
                self.git.commit_state("Karsa: Escalated to Founder due to review divergence")
                return

            if cycle == max_cycles:
                typer.echo("Max revision cycles reached without approval. Escalating to Founder.")
                self.state.transition_to(WorkflowState.ESCALATED)
                self.git.commit_state("Karsa: Escalated to Founder due to max revisions")
                return

            typer.echo("Instructing ProductEngineerAgent to revise artifacts based on unresolved issues...")
            self.state.transition_to(WorkflowState.REVISION)
            
            # Read old artifacts for diffing
            old_vision = self.artifacts.read_artifact("docs/vision/VISION.md")
            old_arch = self.artifacts.read_artifact("docs/architecture/ARCHITECTURE.md")
            old_impl = self.artifacts.read_artifact("docs/implementation/IMPLEMENTATION_PLAN.md")
            
            # Extract unresolved issues
            unresolved = self.issue_registry.get_active_issues()
            unresolved_text = "\n\n".join([f"Issue: {i.id}\nSeverity: {i.severity}\nDescription: {i.description}\nEvidence: {i.evidence}" for i in unresolved])
            
            try:
                self.pe_agent.revise_design(unresolved_text, cycle)
            except Exception as e:
                typer.echo(f"Critical Failure: {str(e)}")
                if "429 QUOTA" in str(e).upper() or "ALL PROVIDERS FAILED" in str(e).upper():
                    self.state.transition_to(WorkflowState.AWAITING_PROVIDER)
                    self.git.commit_state("Karsa: Workflow paused awaiting provider capacity")
                else:
                    self.state.transition_to(WorkflowState.FAILED)
                    self.git.commit_state("Karsa: Workflow FAILED due to provider failure")
                return
            
            if self.obs:
                new_vision = self.artifacts.read_artifact("docs/vision/VISION.md")
                new_arch = self.artifacts.read_artifact("docs/architecture/ARCHITECTURE.md")
                new_impl = self.artifacts.read_artifact("docs/implementation/IMPLEMENTATION_PLAN.md")
                
                self.obs.diff_tracker.generate_diff_summary(old_vision, new_vision, "VISION.md", cycle)
                self.obs.diff_tracker.generate_diff_summary(old_arch, new_arch, "ARCHITECTURE.md", cycle)
                self.obs.diff_tracker.generate_diff_summary(old_impl, new_impl, "IMPLEMENTATION_PLAN.md", cycle)

            self.state.transition_to(WorkflowState.DRAFT)
            self.git.commit_state(f"Karsa: Applied Revision Cycle {cycle}")
            typer.echo(f"Revision {cycle} complete. Artifacts updated.")
            
            cycle += 1
