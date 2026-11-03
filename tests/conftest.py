import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nova import config  # noqa: E402


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point every Nova state file at a throwaway directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    state = tmp_path / ".nova"
    state.mkdir()

    monkeypatch.setattr(config, "NOVA_HOME", tmp_path)
    monkeypatch.setattr(config, "STATE_DIR", state)
    monkeypatch.setattr(config, "WORKSPACE", workspace)
    monkeypatch.setattr(config, "SETTINGS_FILE", state / "settings.json")
    monkeypatch.setattr(config, "MEMORY_FILE", state / "memory.json")
    monkeypatch.setattr(config, "SKILLS_FILE", state / "skills.json")
    monkeypatch.setattr(config, "KNOWLEDGE_DB", state / "knowledge.db")
    monkeypatch.setattr(config, "TRACES_FILE", state / "traces.jsonl")
    monkeypatch.setattr(config, "OVERRIDES", {})

    import nova.learning as learning
    import nova.memory.kb as kb
    import nova.memory.store as store
    import nova.tools as tools

    monkeypatch.setattr(store, "_store", None)
    monkeypatch.setattr(kb, "_db", None)
    monkeypatch.setattr(learning, "_log", None)
    monkeypatch.setattr(tools, "_registry", None)
    return tmp_path
