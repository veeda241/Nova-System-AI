"""Memory, skills and traces are offline and deterministic - test them directly."""

from __future__ import annotations

from nova import config, skills
from nova.learning import TraceLog
from nova.memory import context_block, get_store
from nova.memory.kb import KnowledgeDB
from nova.memory.store import MemoryStore
from nova.security import PermissionGate


def test_facts_roundtrip(tmp_path):
    store = MemoryStore(tmp_path / "m.json")
    store.remember("owner", "Vyas")
    store.remember("wifi", "LabNet")
    assert store.recall("owner")["value"] == "Vyas"
    assert "wifi" in store.facts()
    assert store.search("lab")["facts"]
    assert store.forget("wifi")["ok"]
    assert store.recall("wifi")["ok"] is False
    assert store.recall("owner")["ok"]


def test_missing_fact_lists_similar_keys(tmp_path):
    store = MemoryStore(tmp_path / "m.json")
    store.remember("project_name", "nova")
    miss = store.recall("name")
    assert miss["ok"] is False and "project_name" in miss["similar"]


def test_task_history_and_stats(tmp_path):
    store = MemoryStore(tmp_path / "m.json")
    store.log_task("clean the workspace", True, "removed 3 files", ["list_dir", "delete_path"], 4, "gemini")
    store.log_task("build a report", False, "engine died", ["run_command"], 2, "gemini")
    tasks = store.tasks()
    assert len(tasks) == 2 and tasks[0]["goal"] == "build a report"
    stats = store.stats()
    assert stats["tasks"] == 2 and stats["task_success_rate"] == 50.0


def test_knowledge_db_categories_and_snippets(tmp_path):
    db = KnowledgeDB(tmp_path / "k.db")
    db.store("prefs", "editor", "vscode")
    db.store("prefs", "theme", {"dark": True})
    assert db.retrieve("prefs", "editor")["value"] == "vscode"
    assert db.retrieve("prefs", "theme")["value"] == {"dark": True}
    assert set(db.retrieve("prefs")["entries"]) == {"editor", "theme"}
    assert db.search("vscode")["count"] == 1
    assert db.categories()["categories"]["prefs"] == 2
    db.save_snippet("fib", "def fib(n): return n")
    assert "def fib" in db.get_snippet("fib")["code"]
    assert db.forget("prefs", "editor")["removed"] == 1
    assert db.retrieve("prefs", "editor")["ok"] is False


def test_memory_context_block_feeds_the_agent(sandbox):
    store = get_store()
    store.remember("deploy_target", "kaggle")
    block = context_block("deploy")
    assert "deploy_target" in block
    assert "kaggle" in block


def test_seeded_skill_runs_without_an_llm(sandbox):
    gate = PermissionGate(mode="yolo")
    result = skills.run("workspace_audit", gate)
    assert result["ok"] is True
    assert [step["action"] for step in result["results"]] == ["workspace_info", "system_info", "engine_status"]
    assert all(step["ok"] for step in result["results"])


def test_skill_with_params_writes_into_the_sandbox(sandbox):
    gate = PermissionGate(mode="yolo")
    result = skills.run("fresh_note", gate, {"name": "intro"})
    assert result["ok"] is True
    assert (config.WORKSPACE / "notes" / "intro.md").is_file()
    assert "intro" in get_store().recall("note:intro")["value"]


def test_skill_missing_param_is_reported_not_run(sandbox):
    result = skills.run("fresh_note", PermissionGate(mode="yolo"))
    assert result["ok"] is False and "name=<value>" in result["error"]


def test_skill_denied_by_gate_stops_the_sequence(sandbox):
    (sandbox / "denied.txt").write_text("", encoding="utf-8")
    skills.add("make_note", "write a file", [{"action": "write_file", "args": {"path": "p.txt", "content": "x"}}])
    result = skills.run("make_note", PermissionGate(mode="deny"))
    assert result["ok"] is False and result["failed_at"] == 1
    assert not (config.WORKSPACE / "p.txt").exists()


def test_add_list_remove_custom_skill(sandbox):
    skills.add("noop", "just look around", [{"action": "workspace_info", "args": {}}])
    assert "noop" in [row["name"] for row in skills.listing()]
    assert skills.get("noop")["steps"][0]["action"] == "workspace_info"
    assert skills.remove("noop")["ok"]
    assert skills.remove("noop")["ok"] is False


def test_traces_record_and_aggregate(tmp_path):
    log = TraceLog(tmp_path / "traces.jsonl")
    session = log.new_session()
    log.record(session, "goal one", 1, "tool_call", tool="list_dir", risk="read")
    log.record(session, "goal one", 1, "tool_result", tool="list_dir", ok=True, ms=12.5)
    log.record(session, "goal one", 2, "tool_call", tool="run_command", risk="exec")
    log.record(session, "goal one", 2, "tool_result", tool="run_command", ok=False, ms=3.0, error="hard-blocked")
    log.record(session, "goal one", 3, "llm_response", engine="gemini", ms=900)
    stats = log.stats()
    assert stats["rows"] == 5 and stats["sessions"] == 1
    assert stats["tool_calls"] == 2
    assert stats["tool_success_rate"] == 50.0
    assert dict(stats["most_used_tools"])["list_dir"] == 1
    assert dict(stats["tools_with_failures"])["run_command"] == 1
    assert dict(stats["engines_used"])["gemini"] == 1
    assert log.read(session=session)[0]["session"] == session


def test_traces_survive_a_dirty_file(tmp_path):
    path = tmp_path / "traces.jsonl"
    path.write_text("{not json}\n" + '{"event": "tool_call", "session": "s"}\n', encoding="utf-8")
    rows = TraceLog(path).read()
    assert len(rows) == 1
