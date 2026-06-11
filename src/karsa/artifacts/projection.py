import shutil
from pathlib import Path
from typing import List
from karsa.domain.models import WorkflowSnapshot
from karsa.domain.events import ArtifactPersistedEvent, UserOverrideEvent
from karsa.artifacts.registry import ArtifactRegistry
from karsa.domain.persistence import EventJournalRepository

class ArtifactProjection:
    def __init__(self, workspace_path: Path, registry: ArtifactRegistry, event_repo: EventJournalRepository):
        self.workspace_path = workspace_path
        self.registry = registry
        self.event_repo = event_repo
        
    def apply(self, snapshot: WorkflowSnapshot):
        # Read the event journal up to the snapshot sequence number to reconcile artifacts
        events = self.event_repo.load(snapshot.workflow_id)
        
        # Track the latest desired state of each artifact
        desired_artifacts = {}
        for event in events:
            if event.sequence_number > snapshot.last_sequence_number:
                break
            if isinstance(event, ArtifactPersistedEvent):
                desired_artifacts[event.target_path] = event.sha256_hash
            elif isinstance(event, UserOverrideEvent):
                desired_artifacts[event.artifact_name] = event.new_version_hash
                
        # Idempotent apply
        for target_path, version_hash in desired_artifacts.items():
            live_hash = self.registry.hash_live_file(target_path)
            if live_hash != version_hash:
                source_path = self.registry.get_versioned_path(version_hash)
                if source_path.exists():
                    dest_path = self.workspace_path / target_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                else:
                    # Missing versioned file breaks determinism. We must warn or handle it.
                    pass

class GitProjection:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        
    def apply(self, snapshot: WorkflowSnapshot):
        # Best-effort Git observability, do not crash on failure.
        import subprocess
        try:
            subprocess.run(["git", "add", "."], cwd=self.workspace_path, check=True, capture_output=True)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=self.workspace_path, capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"Karsa: Projection up to sequence {snapshot.last_sequence_number}"], 
                               cwd=self.workspace_path, check=True, capture_output=True)
        except Exception:
            pass # Git isolation boundary: failures do not halt workflow

class ObservabilityProjection:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        
    def apply(self, snapshot: WorkflowSnapshot):
        import json
        obs_dir = self.workspace_path / ".karsa" / "observability"
        obs_dir.mkdir(parents=True, exist_ok=True)
        
        status_file = obs_dir / "status.json"
        
        data = {
            "workflow_id": snapshot.workflow_id,
            "state": snapshot.state.value,
            "last_sequence_number": snapshot.last_sequence_number
        }
        
        with open(status_file, "w") as f:
            json.dump(data, f, indent=2)

class ProjectionManager:
    def __init__(self, workspace_path: Path, registry: ArtifactRegistry, event_repo: EventJournalRepository):
        self.artifact_proj = ArtifactProjection(workspace_path, registry, event_repo)
        self.git_proj = GitProjection(workspace_path)
        self.obs_proj = ObservabilityProjection(workspace_path)
        
    def reconcile_all(self, snapshot: WorkflowSnapshot):
        self.artifact_proj.apply(snapshot)
        self.git_proj.apply(snapshot)
        self.obs_proj.apply(snapshot)
