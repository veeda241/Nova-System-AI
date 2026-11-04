"""nova serve: the two endpoints, the bearer token and the read-only wall.

A scripted engine stands in for a model, so these run offline and assert the
security properties rather than the prose.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest

from nova import server as srv
from nova.agents import react
from nova.security import PermissionGate

SECRET = "the-plain-text-secret-42"


class ScriptedEngines:
    """Replays canned replies so the HTTP layer can be exercised without a model."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.messages = []
        self.active = SimpleNamespace(name="stub", model="stub-1")

    def select(self, preferred="auto"):
        return self.active

    def complete(self, messages, temperature=0.3, preferred="auto"):
        self.messages.append(messages)
        text = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return {"engine": "stub", "text": text}


def action(name, **args):
    return json.dumps({"thought": "looking", "action": name, "args": args})


def final(message):
    return json.dumps({"thought": "done", "action": "final", "args": {"message": message}})


@pytest.fixture
def api(sandbox, monkeypatch):
    """Starts a real server on an ephemeral port and points the agent at a scripted engine."""
    running = []

    def start(replies, token="sekret"):
        engines = ScriptedEngines(replies)
        monkeypatch.setattr(react, "get_engines", lambda: engines)
        server = srv.build_server("127.0.0.1", 0, token=token)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        running.append(server)
        return SimpleNamespace(url=f"http://127.0.0.1:{server.server_port}", engines=engines)

    yield start

    for server in running:
        server.shutdown()
        server.server_close()


def call(base, path, payload=None, token="sekret"):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base + path, data=body, method="POST" if body is not None else "GET")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_health_is_public_and_says_what_the_server_will_not_do(api):
    surface = api([])
    status, payload = call(surface.url, "/health", token=None)
    assert status == 200
    assert payload["ok"] is True and payload["service"] == "nova"
    assert payload["read_only"] is True
    assert payload["auth"] == "bearer token required"


def test_a_read_tool_answers_through_the_http_api(api, sandbox):
    (sandbox / "workspace" / "note.md").write_text("two lines here\nand one more\n", encoding="utf-8")
    surface = api([action("read_file", path="note.md"), final("it holds two lines")])

    status, payload = call(surface.url, "/agent", {"goal": "read note.md"})

    assert status == 200 and payload["ok"] is True
    assert payload["final"] == "it holds two lines"
    assert payload["tools_used"] == ["read_file"] and payload["steps"] == 2
    assert "ms" in payload


def test_a_write_goal_never_reaches_the_disk(api, sandbox):
    surface = api([action("write_file", path="pwned.txt", content="x"), final("I could not write")])

    status, payload = call(surface.url, "/agent", {"goal": "create pwned.txt"})

    assert status == 200 and payload["denials"], "the gate must report what it refused"
    assert not (sandbox / "workspace" / "pwned.txt").exists()
    assert "deny" in payload["denials"][0]["reason"]


def test_allow_outside_is_stripped_so_a_remote_caller_cannot_read_the_host(api, sandbox):
    (sandbox / "outside.md").write_text(SECRET, encoding="utf-8")
    surface = api([action("read_file", path=str(sandbox / "outside.md"), allow_outside=True), final("blocked")])

    status, payload = call(surface.url, "/agent", {"goal": "read a file outside the workspace"})

    assert status == 200
    assert SECRET not in json.dumps(payload)
    assert "outside the workspace" in surface.engines.messages[1][-1]["content"]


def test_the_step_budget_is_honoured_over_http(api):
    surface = api([action("workspace_info"), final("salvaged")])

    status, payload = call(surface.url, "/agent", {"goal": "look around", "max_steps": 1})

    assert status == 200
    assert payload["ok"] is False and payload["error"] == "max_steps" and payload["steps"] == 1


def test_a_wrong_token_is_refused_before_the_agent_runs(api):
    surface = api([final("should never run")])

    status, payload = call(surface.url, "/agent", {"goal": "list files"}, token="wrong")

    assert status == 401 and not surface.engines.messages


def test_a_missing_goal_is_a_400(api):
    surface = api([final("x")])
    status, payload = call(surface.url, "/agent", {"max_steps": 3})
    assert status == 400 and "goal" in payload["error"]


def test_a_budget_above_the_cap_is_refused_with_the_cap(api):
    surface = api([final("x")])
    status, payload = call(surface.url, "/agent", {"goal": "go", "max_steps": 999})
    assert status == 400 and "between 1 and 24" in payload["error"]


def test_a_non_json_body_is_a_400(api):
    surface = api([final("x")])
    request = urllib.request.Request(surface.url + "/agent", data=b"not json", method="POST")
    request.add_header("Authorization", "Bearer sekret")
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request, timeout=30)
    assert caught.value.code == 400


def test_an_unknown_path_is_a_404(api):
    surface = api([final("x")])
    status, payload = call(surface.url, "/nope")
    assert status == 404 and "/agent" in payload["error"]


def test_a_public_bind_without_a_token_is_refused(sandbox):
    with pytest.raises(srv.ServerConfigError) as caught:
        srv.build_server("0.0.0.0", 0, token="")
    assert "NOVA_API_TOKEN" in str(caught.value)

    open_server = srv.build_server("0.0.0.0", 0, token="sekret")
    try:
        assert open_server.token == "sekret"
    finally:
        open_server.server_close()


def test_the_local_default_needs_no_token(sandbox, monkeypatch):
    monkeypatch.delenv("NOVA_API_TOKEN", raising=False)
    local = srv.build_server("127.0.0.1", 0, token=None)
    try:
        assert local.token == ""
    finally:
        local.server_close()


def test_read_only_gate_auto_approves_reads_and_refuses_the_rest(sandbox):
    gate = srv.read_only_gate()
    assert gate.review("read_file", "read", {}, "note.md").allowed is True
    assert gate.review("run_command", "exec", {"command": "dir"}, "dir").allowed is False
    assert gate.review("delete_path", "destructive", {"path": "."}, ".").allowed is False
    assert gate.session_allowed == {}, "a served gate must not remember grants"


def test_the_served_registry_strips_the_escape_hatch(sandbox):
    outside = sandbox / "secret.md"
    outside.write_text(SECRET, encoding="utf-8")

    served = srv.served_registry()
    result, _reason = served.call_gated("read_file", {"path": str(outside), "allow_outside": True}, srv.read_only_gate())
    assert result["ok"] is False and "outside the workspace" in result["error"]

    local = srv.build_registry()
    allowed, _ = local.call_gated("read_file", {"path": str(outside), "allow_outside": True}, PermissionGate(mode="yolo"))
    assert allowed["ok"] is True and SECRET in allowed["content"], "`nova go` keeps the local escape hatch"
