"""End-to-end CLI behaviour, driven as a subprocess so env vars really apply."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run(args, home, expect_keys=False, extra_env=None, stdin_text=None):
    env = dict(os.environ)
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "HF_TOKEN"):
        if not expect_keys:
            env.pop(key, None)
    env["NOVA_HOME"] = str(home)
    env["NOVA_WORKSPACE"] = str(home / "workspace")
    env["PYTHONPATH"] = str(SRC) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["OLLAMA_URL"] = "http://127.0.0.1:9"
    env["LLAMA_CPP_URL"] = "http://127.0.0.1:9"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONWARNINGS"] = "ignore"
    env["NOVA_YOLO"] = ""
    if extra_env:
        env.update(extra_env)
    launch = dict(input=stdin_text) if stdin_text is not None else dict(stdin=subprocess.DEVNULL)
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "nova", *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        encoding="utf-8",
        errors="replace",
        **launch,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def flat(text: str) -> str:
    """Human output is soft-wrapped at 80 columns, so match phrases without newlines."""
    return " ".join(text.split())


def test_help_lists_the_command_surface(tmp_path):
    code, out = run(["--help"], tmp_path)
    assert code == 0
    for fragment in ("ask", "go", "tools", "engine", "memory", "skills", "traces", "doctor"):
        assert fragment in out


def test_version(tmp_path):
    code, out = run(["--version"], tmp_path)
    assert code == 0 and "nova 3" in out


def test_tools_list_shows_the_registry(tmp_path):
    code, out = run(["tools", "list"], tmp_path)
    assert code == 0
    for name in ("read_file", "run_command", "delete_path", "remember_fact"):
        assert name in out


def test_tool_schema_reports_risk(tmp_path):
    code, out = run(["tools", "schema", "delete_path"], tmp_path)
    assert code == 0
    payload = json.loads(out)
    assert payload["risk"] == "destructive" and "path" in payload["params"]
    assert json.loads(run(["tools", "schema", "run_command"], tmp_path)[1])["risk"] == "exec"
    assert json.loads(run(["tools", "schema", "read_file"], tmp_path)[1])["risk"] == "read"


def test_config_paths_is_machine_readable(tmp_path):
    code, out = run(["config", "paths", "--json"], tmp_path)
    assert code == 0
    payload = json.loads(out)
    assert payload["workspace"].endswith("workspace")
    assert Path(payload["state"]).parent == tmp_path


def test_write_needs_yolo_and_works_with_it(tmp_path):
    (tmp_path / "workspace").mkdir()
    blocked = run(["tools", "call", "write_file", "path=hello.txt", "content=from-cli"], tmp_path)
    assert blocked[0] == 1 and "not a TTY" in flat(blocked[1])
    assert not (tmp_path / "workspace" / "hello.txt").exists()

    code, out = run(["tools", "call", "write_file", "path=hello.txt", "content=from-cli", "--mode", "yolo"], tmp_path)
    assert code == 0 and "hello.txt" in out
    assert (tmp_path / "workspace" / "hello.txt").read_text(encoding="utf-8") == "from-cli"


def test_nova_yolo_environment_variable_grants_approval_without_a_tty(tmp_path):
    (tmp_path / "workspace").mkdir()
    code, out = run(
        ["tools", "call", "write_file", "path=v.txt", "content=yolo-env"],
        tmp_path,
        extra_env={"NOVA_YOLO": "1"},
    )
    assert code == 0 and (tmp_path / "workspace" / "v.txt").read_text(encoding="utf-8") == "yolo-env"


def test_a_session_flag_does_not_rewrite_saved_settings(tmp_path):
    (tmp_path / "workspace").mkdir()
    run(["config", "set", "approval_mode", "ask"], tmp_path)
    run(["tools", "call", "workspace_info", "--mode", "yolo", "--engine", "gemini"], tmp_path)
    payload = json.loads(run(["config", "show", "--json"], tmp_path)[1])["settings"]
    assert payload["approval_mode"] == "ask" and payload["engine"] != "gemini"


def test_workspace_escape_is_blocked_at_the_cli(tmp_path):
    code, out = run(["tools", "call", "read_file", "path=../../win.ini", "--mode", "yolo"], tmp_path)
    assert code == 1 and "outside the workspace" in flat(out)


def test_catastrophic_command_is_hard_blocked(tmp_path):
    code, out = run(["tools", "call", "run_command", "command=rm -rf /", "--mode", "yolo"], tmp_path)
    assert code == 1 and "hard-blocked" in flat(out)


def test_delete_needs_approval_and_deny_mode_refuses(tmp_path):
    (tmp_path / "workspace").mkdir(parents=True)
    (tmp_path / "workspace" / "keep.txt").write_text("keep", encoding="utf-8")
    code, out = run(["tools", "call", "delete_path", "path=keep.txt", "--mode", "deny"], tmp_path)
    assert code == 1 and "blocks destructive" in flat(out)
    assert (tmp_path / "workspace" / "keep.txt").exists()


def test_doctor_is_honest_when_no_engine_exists(tmp_path):
    code, out = run(["doctor"], tmp_path)
    assert code == 3
    assert "no engine is reachable" in flat(out)
    assert "ollama serve" in out and "GEMINI_API_KEY" in out


def test_ask_fails_loudly_instead_of_inventing_an_answer(tmp_path):
    code, out = run(["ask", "what is 2+2?"], tmp_path)
    assert code == 3
    assert "no answer" not in out
    assert "GROQ_API_KEY is not set" in flat(out) or "GEMINI_API_KEY is not set" in flat(out)


def test_go_reports_no_engine_before_touching_tools(tmp_path):
    code, out = run(["go", "delete everything", "--mode", "yolo", "--json"], tmp_path)
    assert code == 1
    payload = json.loads(out)
    assert payload["ok"] is False and "no engine" in payload["final"]
    assert payload["tools_used"] == []


def test_memory_roundtrip_through_the_cli(tmp_path):
    assert run(["memory", "set", "owner", "Vyas"], tmp_path)[0] == 0
    code, out = run(["memory", "get", "owner", "--json"], tmp_path)
    assert code == 0
    assert json.loads(out)["value"] == "Vyas"
    assert run(["memory", "note", "prefs", "editor", "vscode"], tmp_path)[0] == 0
    code, out = run(["memory", "notes", "prefs", "--json"], tmp_path)
    assert json.loads(out)["entries"]["editor"] == "vscode"


def test_a_skill_runs_offline_and_emits_json(tmp_path):
    (tmp_path / "workspace").mkdir()
    code, out = run(["skills", "run", "workspace_audit", "--mode", "yolo", "--json"], tmp_path)
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True and len(payload["results"]) == 3


OPENJARVIS_PACK = """
[skill]
name = "code-lint"
description = "Read a source file and report issues"
version = "0.1.0"
author = "openjarvis"

[[skill.steps]]
tool_name = "file_read"
arguments_template = '{"path": "{file_path}"}'
output_key = "source_code"

[[skill.steps]]
tool_name = "think"
arguments_template = '{"thought": "Grade this code: {source_code}"}'
output_key = "issues"
"""


def test_skills_import_turns_a_pack_into_nova_steps(tmp_path):
    (tmp_path / "workspace").mkdir()
    pack = tmp_path / "code-lint.toml"
    pack.write_text(OPENJARVIS_PACK, encoding="utf-8")
    code, out = run(["skills", "import", str(pack), "--json"], tmp_path)
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True and payload["params"] == ["file_path"]
    code, out = run(["skills", "show", "code-lint", "--json"], tmp_path)
    assert json.loads(out)["steps"][1]["action"] == "think"


def test_skills_import_refuses_a_pack_nova_cannot_run(tmp_path):
    (tmp_path / "workspace").mkdir()
    pack = tmp_path / "web.toml"
    pack.write_text(
        OPENJARVIS_PACK.replace('"think"', '"web_search"').replace("code-lint", "web-read"), encoding="utf-8"
    )
    code, out = run(["skills", "import", str(pack), "--json"], tmp_path)
    assert code == 1 and "web_search" in out


def test_traces_stats_are_json_clean(tmp_path):
    code, out = run(["traces", "stats", "--json"], tmp_path)
    assert code == 0
    payload = json.loads(out)
    assert "rows" in payload


def test_validate_finds_a_broken_file(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n    pass\n", encoding="utf-8")
    code, out = run(["validate", str(broken)], tmp_path)
    assert code == 0
    assert "line 1" in out

    good = tmp_path / "good.py"
    good.write_text("def helper():\n    return 1\n", encoding="utf-8")
    code, out = run(["validate", str(good), "--json"], tmp_path)
    payload = json.loads(out)
    assert payload["ok"] is True and payload["functions"] == ["helper"]


def test_chat_repl_exits_on_a_bare_quit_word(tmp_path):
    (tmp_path / "workspace").mkdir()
    code, out = run(["chat"], tmp_path, stdin_text="/workspace\nquit\n")
    assert code == 0
    assert "workspace:" in flat(out) and "bye" in flat(out)


def test_engine_list_names_every_backend(tmp_path):
    code, out = run(["engine", "list"], tmp_path)
    assert code == 0
    for name in ("llama", "ollama", "hf", "groq", "gemini", "openai"):
        assert name in out


def test_serve_refuses_a_public_bind_without_a_token(tmp_path):
    code, out = run(["serve", "--host", "0.0.0.0"], tmp_path, extra_env={"NOVA_API_TOKEN": ""})
    assert code == 2
    assert "NOVA_API_TOKEN" in flat(out)
