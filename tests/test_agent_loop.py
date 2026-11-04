"""The ReAct loop itself: repetition protection, budget pressure, clean termination.

These run against a scripted engine, not a model, so they are deterministic and offline.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from nova.agents import looks_like_action
from nova.agents.react import ReactAgent, format_observation
from nova.learning import get_log
from nova.memory import get_store
from nova.security import PermissionGate
from nova.tools import Registry, Tool


class ScriptedEngines:
    """Stands in for the engine registry: replays canned replies, records every prompt."""

    def __init__(self, replies, salvage=None):
        self.replies = list(replies)
        self.salvage = salvage
        self.messages = []
        self.active = SimpleNamespace(name="stub")

    def select(self, preferred="auto"):
        return self.active

    def complete(self, messages, temperature=0.3, preferred="auto"):
        self.messages.append(messages)
        if self.salvage is not None and "no steps left" in messages[-1]["content"]:
            return {"engine": "stub", "text": self.salvage}
        text = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return {"engine": "stub", "text": text}


def counting_tools():
    calls: list = []

    def probe(path="."):
        calls.append(path)
        return {"ok": True, "count": 2, "entries": [{"name": "a.txt"}, {"name": "b.txt"}]}

    registry = Registry()
    registry.register(Tool("probe", "Count files for testing.", probe, {"path": "str"}, "read"))
    return registry, calls


def action(name, **args):
    return json.dumps({"thought": "looking", "action": name, "args": args})


def make_agent(replies, tools, max_steps=6, use_memory=False, salvage=None):
    gate = PermissionGate(mode="yolo")
    engines = ScriptedEngines(replies, salvage=salvage)
    return ReactAgent(engines=engines, tools=tools, gate=gate, max_steps=max_steps, verbose=False, use_memory=use_memory)


def test_an_identical_call_is_blocked_the_third_time_instead_of_re_run(sandbox):
    tools, calls = counting_tools()
    agent = make_agent([action("probe", path=".")], tools, max_steps=6)

    outcome = agent.run("look at the files")

    assert len(calls) == 2, "the third identical call must not reach the handler"
    assert outcome.error == "max_steps"
    assert any("REPEAT BLOCKED" in entry["observation"] for entry in outcome.history)
    events = [row["event"] for row in get_log().read(limit=50, session=outcome.trace_session)]
    assert "repeat_blocked" in events


def test_different_arguments_are_not_treated_as_a_repeat(sandbox):
    tools, calls = counting_tools()
    replies = [action("probe", path="."), action("probe", path="src"), action("probe", path="tests"), action("final", message="done")]
    agent = make_agent(replies, tools, max_steps=6)

    outcome = agent.run("look in three places")

    assert calls == [".", "src", "tests"]
    assert outcome.ok is True and outcome.steps == 4


def failing_tools():
    calls: list = []

    def probe(path="."):
        calls.append(path)
        return {"ok": False, "denied": True, "error": "stdin is not a TTY, so approval cannot be collected"}

    registry = Registry()
    registry.register(Tool("probe", "Count files for testing.", probe, {"path": "str"}, "read"))
    return registry, calls


def test_a_tool_that_fails_twice_for_one_reason_is_closed_for_the_run(sandbox):
    tools, calls = failing_tools()
    replies = [
        action("probe", path="."),
        action("probe", path="src"),
        action("probe", path="tests"),
        action("final", message="gave up"),
    ]
    agent = make_agent(replies, tools, max_steps=6)

    outcome = agent.run("run something that cannot be approved")

    assert len(calls) == 2, "the third attempt must not reach the handler"
    assert "read_file" in outcome.history[1]["observation"], "a denial must name tools that still work"
    blocked = [entry for entry in outcome.history if "TOOL BLOCKED" in entry["observation"]]
    assert blocked and "stdin is not a TTY" in blocked[0]["observation"]
    events = [row["event"] for row in get_log().read(limit=50, session=outcome.trace_session)]
    assert "tool_blocked" in events


def test_the_last_steps_are_told_to_stop_looking(sandbox):
    tools, _ = counting_tools()
    agent = make_agent([action("probe", path=".")], tools, max_steps=5)

    early = agent._messages("goal", [], "s", step=1)[1]["content"]
    late = agent._messages("goal", [], "s", step=5)[1]["content"]

    assert "STEPS LEFT" not in early
    assert "STEPS LEFT: 1" in late and "Repeating an earlier call" in late
    assert "An observation that starts with OK" in late


def test_final_ends_the_run_and_the_task_lands_in_memory(sandbox):
    tools, _ = counting_tools()
    replies = [action("probe", path="."), action("final", message="two files: a.txt and b.txt")]
    agent = make_agent(replies, tools, max_steps=6, use_memory=True)

    outcome = agent.run("count the files")

    assert outcome.ok is True and outcome.steps == 2
    assert outcome.final.startswith("two files")
    assert outcome.tools_used == ["probe"]
    logged = get_store().tasks(1)[0]
    assert logged["goal"] == "count the files" and logged["ok"] is True


def test_an_unknown_tool_becomes_an_observation_not_a_crash(sandbox):
    tools, _ = counting_tools()
    agent = make_agent([action("teleport", to=" paris"), action("final", message="no such tool")], tools)

    outcome = agent.run("try to teleport")

    assert outcome.ok is True
    assert "UNKNOWN TOOL" in outcome.history[0]["observation"]
    assert "probe" in outcome.history[0]["observation"]


def test_running_out_of_steps_still_answers_from_the_transcript(sandbox):
    tools, _ = counting_tools()
    agent = make_agent([action("probe", path=".")], tools, max_steps=2, salvage="study-plan.md has 7 lines.")

    outcome = agent.run("how many lines does study-plan.md have?")

    assert outcome.ok is False and outcome.error == "max_steps"
    assert outcome.final == "study-plan.md has 7 lines."


def test_a_salvage_reply_that_asks_for_another_tool_is_thrown_away(sandbox):
    tools, _ = counting_tools()
    agent = make_agent([action("probe", path=".")], tools, max_steps=2, salvage=action("probe", path="."))

    outcome = agent.run("how many lines?")

    assert outcome.final.startswith("stopped after 2 steps")


def test_observations_lead_with_the_numbers_that_answer_the_goal():
    payload = {"lines": 7, "size": 146, "truncated": False, "path": "notes.md", "content": "a\nb"}
    text = format_observation(payload)
    assert text.startswith("lines=7, size=146")
    assert "path=notes.md" in text
    assert "content=a\nb" in text


def test_a_long_body_is_clipped_and_says_by_how_much():
    text = format_observation({"lines": 2, "content": "x" * 1500})
    assert text.endswith("[+100 chars]")


def test_polite_instructions_still_reach_the_tool_loop():
    assert looks_like_action("can you arrange the download files into proper file type")
    assert looks_like_action("please sort these pdfs into folders")
    assert looks_like_action("tidy up this folder")


def test_genuine_questions_stay_on_the_tool_free_answer_path():
    assert not looks_like_action("what is 7*8?")
    assert not looks_like_action("can you tell me what 7*8 is?")
    assert not looks_like_action("what is the list of planets?")
