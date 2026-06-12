from typing import Optional, Dict, Any, Tuple
from karsa.domain.models import WorkflowSnapshot, WorkflowState
from karsa.domain.events import (
    ArtifactPersistedEvent, ExecutionCheckpointEvent, 
    ReviewCycleStartedEvent, ReviewCycleCompletedEvent, 
    UserOverrideEvent,
    EscalationTriggeredEvent
)
from karsa.workflow.retry import RetryCoordinator
from karsa.artifacts.registry import ArtifactRegistry
from karsa.llm.prompts import build_pe_prompt, build_review_prompt
from karsa.review.parser import parse_review
from karsa.tools.executor import ToolExecutor

class AgentOrchestrator:
    def __init__(self, engine, retry_coordinator: RetryCoordinator, registry: ArtifactRegistry, provider_manager=None):
        self.engine = engine # WorkflowEngine
        self.retry_coordinator = retry_coordinator
        self.registry = registry
        self.provider = provider_manager
        self.tool_executor = ToolExecutor()

    def _get_active_checkpoint(self, cycle_id: int, task: str) -> Optional[str]:
        # Simple scan of events to find if this sub-task is completed for this cycle
        events = self.engine.event_repo.load(self.engine.snapshot.workflow_id)
        for e in reversed(events):
            if isinstance(e, ExecutionCheckpointEvent) and e.cycle_id == cycle_id and e.sub_task_name == task:
                return e.artifact_version_hash
        return None

    def execute_cycle(self, cycle_id: int) -> str:
        """Runs the LLM loop and returns an outcome: APPROVED, ESCALATED, REVISE, SUSPENDED"""
        import json
        import re
        
        # 1. Determine latest committed manifest and check for live user overrides
        current_manifest = {}
        current_hash = self._get_active_checkpoint(cycle_id-1, "PE_COMPLETE") if cycle_id > 1 else None
        if current_hash:
            manifest_str = self.registry.get_versioned(current_hash) or "{}"
            try:
                manifest_data = json.loads(manifest_str)
                current_manifest = manifest_data.get("files", {})
            except:
                pass
                
        # Handle user overrides on live files
        for target_path, expected_hash in list(current_manifest.items()):
            live_hash = self.registry.hash_live_file(target_path)
            if expected_hash and live_hash and live_hash != expected_hash:
                with open(self.registry.workspace_path / target_path, "r") as f:
                    content = f.read()
                if len(content.strip()) > 0:
                    version_hash = self.registry.store_versioned(content)
                    self.engine.append_event(UserOverrideEvent(artifact_name=target_path, new_version_hash=version_hash))
                    current_manifest[target_path] = version_hash

        self.engine.append_event(ReviewCycleStartedEvent(cycle_id=cycle_id))
        
        objective = getattr(self, 'objective', "Build a Duplicate File Finder CLI in duplicate_finder.py with pytest coverage.")
        
        # Reconstruct current_artifact string for the PE context from the manifest
        current_artifact_parts = []
        for path, version_hash in current_manifest.items():
            content = self.registry.get_versioned(version_hash) or ""
            current_artifact_parts.append(f'<file path="{path}">\n{content}\n</file>')
        current_artifact = "\n\n".join(current_artifact_parts)
        
        feedback = ""
        # 2. PE Generation Step
        pe_hash = self._get_active_checkpoint(cycle_id, "PE_COMPLETE")
        new_manifest = current_manifest.copy()
        generated_files = {} # track files modified this cycle for the review context
        
        if not pe_hash:
            try:
                pe_prompt = build_pe_prompt(objective, current_artifact, feedback)
                if self.provider:
                    pe_content = self.retry_coordinator.execute_with_backoff(lambda: self.provider.generate(pe_prompt))
                else:
                    pe_content = """<file path="src/main.py">\nprint('hello')\n</file>"""
                
                # Parse multi-file outputs
                pattern = r'<file\s+path="([^"]+)">\s*(.*?)\s*</file>'
                matches = re.finditer(pattern, pe_content, re.DOTALL)
                
                for match in matches:
                    filepath = match.group(1).strip()
                    content = match.group(2).strip()
                    
                    file_hash = self.registry.store_versioned(content)
                    generated_files[filepath] = file_hash
                    new_manifest[filepath] = file_hash
                    
                    # write physical file
                    dest = self.registry.workspace_path / filepath
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest, "w") as f:
                        f.write(content)
                        
                    self.engine.append_event(ArtifactPersistedEvent(artifact_id=file_hash, target_path=filepath, sha256_hash=file_hash))
                
                # Create tree manifest
                manifest_json = json.dumps({
                    "version": 1,
                    "files": new_manifest
                }, indent=2)
                
                pe_hash = self.registry.store_versioned(manifest_json)
                self.engine.append_event(ArtifactPersistedEvent(artifact_id=pe_hash, target_path=".karsa/manifest.json", sha256_hash=pe_hash))
                self.engine.append_event(ExecutionCheckpointEvent(cycle_id=cycle_id, sub_task_name="PE_COMPLETE", artifact_version_hash=pe_hash, accumulated_cost=1.5))
            except Exception as e:
                if "Exhausted" in str(e):
                    return "SUSPENDED"
                return "FAILED"
        else:
            manifest_str = self.registry.get_versioned(pe_hash) or "{}"
            try:
                manifest_data = json.loads(manifest_str)
                new_manifest = manifest_data.get("files", {})
                for path, hash_val in new_manifest.items():
                    if current_manifest.get(path) != hash_val:
                        generated_files[path] = hash_val
            except:
                pass

        # 3. Tool Execution
        tool_output = self.tool_executor.run_pytest(self.registry.workspace_path)
        pytest_success = "Exit code: 0" in tool_output

        # 4. Review Generation Step
        review_hash = self._get_active_checkpoint(cycle_id, "REVIEW_COMPLETE")
        convergence_score = 0.0
        decision = "REVISE"
        if not review_hash:
            try:
                # Reconstruct review context: files generated in current cycle + README.md/design.md
                review_context_parts = []
                
                # add specific context files if present in the tree
                for special_file in ["README.md", "design.md"]:
                    if special_file in new_manifest and special_file not in generated_files:
                        content = self.registry.get_versioned(new_manifest[special_file]) or ""
                        review_context_parts.append(f'<file path="{special_file}">\n{content}\n</file>')
                        
                for path, hash_val in generated_files.items():
                    content = self.registry.get_versioned(hash_val) or ""
                    review_context_parts.append(f'<file path="{path}">\n{content}\n</file>')
                    
                artifact_content = "\n\n".join(review_context_parts)
                review_prompt = build_review_prompt(objective, artifact_content, tool_output)
                
                if self.provider:
                    review_content = self.retry_coordinator.execute_with_backoff(lambda: self.provider.generate(review_prompt))
                else:
                    review_content = '{"decision": "APPROVED", "convergence_score": 1.0, "blocking_issues": []}'
                    if not pytest_success:
                        review_content = '{"decision": "REVISE", "convergence_score": 0.5, "blocking_issues": ["Pytest failed"]}'
                        
                parsed_review = parse_review(review_content)
                decision = parsed_review.get("decision", "REVISE")
                convergence_score = parsed_review.get("convergence_score", 0.0)
                blocking_issues = parsed_review.get("blocking_issues", [])
                
                # Enforce guardrails
                if decision == "APPROVED" and (not pytest_success or len(blocking_issues) > 0):
                    decision = "REVISE"
                    convergence_score = min(convergence_score, 0.9)
                    
                review_hash = self.registry.store_versioned(review_content)
                self.engine.append_event(ArtifactPersistedEvent(artifact_id=review_hash, target_path="review_result.json", sha256_hash=review_hash))
                self.engine.append_event(ExecutionCheckpointEvent(cycle_id=cycle_id, sub_task_name="REVIEW_COMPLETE", artifact_version_hash=review_hash, accumulated_cost=1.0))
            except Exception as e:
                if "Exhausted" in str(e):
                    return "SUSPENDED"
                return "FAILED"
                
        self.engine.append_event(ReviewCycleCompletedEvent(cycle_id=cycle_id, convergence_score=convergence_score))
        
        # Convergence logic
        if decision == "APPROVED":
            return "APPROVED"
        elif cycle_id > 3:
            self.engine.append_event(EscalationTriggeredEvent(cycle_id=cycle_id, divergence_reason="Max cycles reached"))
            return "ESCALATED"
        else:
            return "REVISE"
