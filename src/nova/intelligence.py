"""Intelligence primitive: persona, the action grammar, and response parsing."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple

FINAL = "final"

PERSONA = """You are Nova, an agentic operating-system assistant that runs in the terminal.
You act through tools instead of describing what you would do. You are precise, you
report what actually happened, and you never invent file contents, command output or
results you did not observe."""

ACTION_GRAMMAR = f"""Reply with exactly ONE JSON object, nothing before or after it.

To use a tool:
  {{"thought": "why", "{FINAL.replace('final', 'action')}": "tool_name", "args": {{...}}}}

To answer the user and stop:
  {{"thought": "why", "action": "{FINAL}", "args": {{"message": "your answer"}}}}

Rules:
1. One action per reply. Wait for its real result before deciding the next one.
2. Never claim a tool ran unless you saw its result in the transcript.
3. Paths are relative to the workspace unless you pass allow_outside=true.
4. If a step is denied by the permission gate, do not retry it; say what was blocked.
5. If the task is finished, or impossible, return action "{FINAL}" and summarise honestly."""


def build_system_prompt(tools_block: str, memory_block: str = "", workspace: str = "") -> str:
    chunks = [PERSONA, ACTION_GRAMMAR, f"AVAILABLE TOOLS:\n{tools_block}"]
    if workspace:
        chunks.append(f"WORKSPACE ROOT: {workspace}")
    if memory_block:
        chunks.append(memory_block)
    return "\n\n".join(chunks)


def history_block(history: List[Dict[str, Any]], limit: int = 8) -> str:
    if not history:
        return "No steps taken yet."
    lines = []
    for entry in history[-limit:]:
        args = json.dumps(entry.get("args", {}), default=str)[:160]
        lines.append(f"step {entry['step']}: {entry['action']} {args}\n  -> {entry['observation'][:300]}")
    return "\n".join(lines)


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Pull the first complete JSON object out of a chatty model reply."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except ValueError:
        pass

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            parsed, _ = decoder.raw_decode(cleaned[match.start() :])
        except ValueError:
            continue
        if isinstance(parsed, dict) and ("action" in parsed or "thought" in parsed):
            return parsed
    return None


def normalise_action(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
    """Return (action, args, thought) whatever shape the model used."""
    thought = str(payload.get("thought") or payload.get("reasoning") or payload.get("plan") or "")
    action = str(payload.get("action") or payload.get("tool") or "").strip()
    args = payload.get("args")
    if not isinstance(args, dict):
        args = {k: v for k, v in payload.items() if k not in ("action", "tool", "args", "thought", "reasoning", "plan", "message", "result")}
        if "message" in payload:
            args = {"message": payload["message"]}
    if not action:
        if "message" in payload:
            action, args = FINAL, {"message": payload["message"]}
        elif "result" in payload:
            action, args = FINAL, {"message": payload["result"]}
        else:
            action, args = "", {}
    return action, args, thought


def parse_reply(text: str, fallback_to_final: bool = True) -> Tuple[str, Dict[str, Any], str, Optional[str]]:
    """Return (action, args, thought, parse_error)."""
    payload = extract_json(text)
    if payload is None:
        if fallback_to_final and text:
            return FINAL, {"message": text.strip()}, "model replied in prose; treated as the answer", None
        return "", {}, "", "reply contained no JSON action"
    action, args, thought = normalise_action(payload)
    return action, args, thought, None


def validate_python(code: str) -> Dict[str, Any]:
    """Real syntax validation - no LLM, no false confidence."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"ok": False, "error": f"line {exc.lineno}: {exc.msg}"}

    risky = sorted(
        {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "__import__", "compile")
        }
    )
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return {
        "ok": True,
        "functions": [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
        "risky_calls": risky,
        "imports": sorted(set(imports))[:20],
    }
