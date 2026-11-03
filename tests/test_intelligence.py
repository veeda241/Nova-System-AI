"""The action grammar is what a model has to obey - it must survive messy replies."""

from __future__ import annotations

from nova import intelligence


def test_plain_json_action():
    action, args, thought, error = intelligence.parse_reply('{"thought": "list files", "action": "list_dir", "args": {"path": "."}}')
    assert action == "list_dir" and args == {"path": "."} and error is None
    assert thought == "list files"


def test_fenced_json_is_unwrapped():
    text = "Sure!\n```json\n{\"action\": \"read_file\", \"args\": {\"path\": \"a.txt\"}}\n```\nDone."
    action, args, _, error = intelligence.parse_reply(text)
    assert error is None and action == "read_file" and args["path"] == "a.txt"


def test_json_embedded_in_prose():
    text = 'I will now act: {"action": "write_file", "args": {"path": "x", "content": "hi"}}'
    action, args, _, error = intelligence.parse_reply(text)
    assert action == "write_file" and args["content"] == "hi"


def test_flat_args_are_recovered():
    action, args, _, _ = intelligence.parse_reply('{"action": "read_file", "path": "a.txt"}')
    assert action == "read_file" and args == {"path": "a.txt"}


def test_prose_reply_becomes_the_answer():
    action, args, thought, error = intelligence.parse_reply("The workspace holds three files.")
    assert action == intelligence.FINAL and "three files" in args["message"] and error is None


def test_empty_reply_is_a_protocol_error():
    action, args, _, error = intelligence.parse_reply("total word salad", fallback_to_final=False)
    assert action == "" and error is not None


def test_final_from_result_key():
    action, args, _, _ = intelligence.parse_reply('{"result": "all done"}')
    assert action == intelligence.FINAL and args["message"] == "all done"


def test_history_block_shows_steps_and_observations():
    block = intelligence.history_block([{"step": 1, "action": "list_dir", "args": {"path": "."}, "observation": "OK: count=3"}])
    assert "step 1" in block and "list_dir" in block and "count=3" in block


def test_history_block_empty():
    assert intelligence.history_block([]) == "No steps taken yet."


def test_system_prompt_carries_tools_and_rules():
    prompt = intelligence.build_system_prompt("- list_dir() [read] lists", "KNOWN FACTS:\n- owner: V", "C:/ws")
    for fragment in ("list_dir()", "KNOWN FACTS", "C:/ws", '"action"', intelligence.FINAL):
        assert fragment in prompt


def test_validate_python_catches_syntax_errors():
    broken = intelligence.validate_python("def f(:\n  pass")
    assert broken["ok"] is False and "line" in broken["error"]


def test_validate_python_reports_structure():
    report = intelligence.validate_python("import json\nimport os\n\ndef helper():\n    return eval('1+1')\n")
    assert report["ok"]
    assert report["functions"] == ["helper"]
    assert "eval" in report["risky_calls"]
    assert set(report["imports"]) == {"json", "os"}
