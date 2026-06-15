from pathlib import Path

def test_artifact_manager_initialize(tmp_path: Path):
    manager = ArtifactManager(tmp_path)
    manager.initialize()
    
    assert (tmp_path / "docs").exists()
    assert (tmp_path / "src").exists()

def test_artifact_manager_write_read(tmp_path: Path):
    manager = ArtifactManager(tmp_path)
    manager.write_artifact("docs/vision.md", "# Vision")
    
    content = manager.read_artifact("docs/vision.md")
    assert content == "# Vision"
