import os
from pathlib import Path

def get_application_root() -> Path:
    # return repository root (parent of src/karsa/workspace/resolver.py is src/karsa/workspace, then src/karsa, then src, then root)
    return Path(__file__).resolve().parent.parent.parent.parent

def get_workspace_root() -> Path:
    env_dir = os.getenv("KARSA_WORKSPACE_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return get_application_root() / "workspace"

def resolve_project_workspace(slug: str) -> Path:
    return get_workspace_root() / slug

def get_diagnostics() -> dict:
    env_dir = os.getenv("KARSA_WORKSPACE_DIR")
    source = "KARSA_WORKSPACE_DIR" if env_dir else "default"
    return {
        "source": source,
        "workspace_root": str(get_workspace_root()),
        "cwd": str(Path.cwd().resolve()),
        "application_root": str(get_application_root()),
    }
