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


class StubEngines:
    """Stand-in for the engine registry, so a `think` step can be tested without a model."""

    def __init__(self, reply="two findings: no docstring, bare except"):
        self.reply = reply
        self.prompts = []

    def complete(self, messages, temperature=0.3, preferred="auto"):
        self.prompts.append(messages[-1]["content"])
        return {"engine": "stub", "text": self.reply}


def test_a_think_step_sees_the_previous_step_output(sandbox):
    skills.add(
        "lint",
        "write, read, judge",
        [
            {"action": "write_file", "args": {"path": "a.py", "content": "def f():\n    pass\n"}},
            {"action": "read_file", "args": {"path": "a.py"}, "output_key": "source"},
            {"action": "think", "args": {"prompt": "Review: {source}"}, "output_key": "verdict"},
        ],
    )
    engines = StubEngines()
    result = skills.run("lint", PermissionGate(mode="yolo"), engines=engines)
    assert result["ok"] is True
    assert result["results"][-1]["engine"] == "stub"
    assert engines.prompts[0].startswith("Review: ") and "def f():" in engines.prompts[0]


def test_a_dead_engine_fails_the_skill_with_its_own_words(sandbox):
    class Dead(StubEngines):
        def complete(self, messages, temperature=0.3, preferred="auto"):
            from nova.engine.base import EngineError

            raise EngineError("every engine failed:\n  - ollama: not reachable")

    skills.add("judge", "think hard", [{"action": "think", "args": {"prompt": "anything"}}])
    result = skills.run("judge", PermissionGate(mode="yolo"), engines=Dead())
    assert result["ok"] is False and result["failed_at"] == 1
    assert "every engine failed" in result["error"]


def test_a_think_step_with_no_prompt_never_calls_a_model(sandbox):
    assert "args.prompt" in skills.think("", StubEngines())["error"]


def test_threading_clips_what_a_small_model_cannot_hold():
    body = skills._thread({"ok": True, "text": "x" * (skills.STEP_OUTPUT_LIMIT + 500)})
    assert body.endswith("[...clipped]") and len(body) == skills.STEP_OUTPUT_LIMIT + len("[...clipped]")


def test_threading_hands_a_tool_step_over_as_json():
    body = skills._thread({"ok": True, "_ms": 12.0, "count": 3, "by_ext": "pdf=3"})
    assert "pdf=3" in body and "_ms" not in body


CODE_LINT_PACK = """
[skill]
name = "code-lint"
description = "Read a source file and report code quality issues"
version = "0.1.0"
author = "openjarvis"

[[skill.steps]]
tool_name = "file_read"
arguments_template = '{"path": "{file_path}"}'
output_key = "source_code"

[[skill.steps]]
tool_name = "think"
arguments_template = '{"thought": "Find the quality issues: {source_code}"}'
output_key = "issues"
"""


def test_a_real_pack_becomes_nova_steps(sandbox):
    pack = sandbox / "code-lint.toml"
    pack.write_text(CODE_LINT_PACK, encoding="utf-8")
    parsed = skills.parse_pack(pack)
    assert parsed["problems"] == []
    assert [step["action"] for step in parsed["steps"]] == ["read_file", "think"]
    assert parsed["params"] == ["file_path"]
    assert parsed["steps"][1]["args"]["prompt"].startswith("Find the quality issues:")


def test_an_imported_pack_runs_end_to_end(sandbox):
    (config.WORKSPACE / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    pack = sandbox / "code-lint.toml"
    pack.write_text(CODE_LINT_PACK, encoding="utf-8")
    assert skills.import_pack(pack)["ok"] is True
    engines = StubEngines()
    result = skills.run("code-lint", PermissionGate(mode="yolo"), {"file_path": "a.py"}, engines)
    assert result["ok"] is True and "def f():" in engines.prompts[0]


def test_a_pack_nova_cannot_complete_is_refused_whole(sandbox):
    pack = sandbox / "research.toml"
    pack.write_text(CODE_LINT_PACK.replace('"think"', '"web_search"').replace("code-lint", "research"), encoding="utf-8")
    outcome = skills.import_pack(pack)
    assert outcome["ok"] is False and any("web_search" in problem for problem in outcome["refused"])
    assert skills.get("research") is None


def test_a_step_missing_its_required_arg_is_refused(sandbox):
    pack = sandbox / "halfwritten.toml"
    pack.write_text(
        CODE_LINT_PACK.replace("file_read", "file_write").replace('"think"', '"file_read"'),
        encoding="utf-8",
    )
    outcome = skills.import_pack(pack)
    assert outcome["ok"] is False and any("never given content" in problem for problem in outcome["refused"])


def test_import_dir_accounts_for_every_pack_it_touched(sandbox):
    (sandbox / "good.toml").write_text(CODE_LINT_PACK, encoding="utf-8")
    (sandbox / "bad.toml").write_text(
        CODE_LINT_PACK.replace('"think"', '"pdf_extract"').replace("code-lint", "pdf-reader"), encoding="utf-8"
    )
    outcome = skills.import_dir(sandbox)
    assert outcome["ok"] is True and outcome["imported"] == ["code-lint"]
    assert "pdf-reader" in outcome["refused"]


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
