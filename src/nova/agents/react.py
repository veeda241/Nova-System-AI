"""The ReAct agent: think, call one tool, observe the real result, repeat."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .. import config, intelligence
from ..engine import EngineError, get_registry as get_engines
from ..learning import get_log
from ..memory import context_block, get_store
from ..security import PermissionGate
from ..tools import get_registry as get_tools


@dataclass
class AgentOutcome:
    ok: bool
    final: str
    steps: int = 0
    engine: str = ""
    tools_used: List[str] = field(default_factory=list)
    denials: List[Dict[str, str]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    trace_session: str = ""
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "final": self.final,
            "steps": self.steps,
            "engine": self.engine,
            "tools_used": sorted(set(self.tools_used)),
            "denials": self.denials,
            "trace_session": self.trace_session,
            "error": self.error,
        }


class ReactAgent:
    def __init__(
        self,
        engines: Optional[Any] = None,
        tools: Optional[Any] = None,
        gate: Optional[PermissionGate] = None,
        max_steps: Optional[int] = None,
        verbose: bool = True,
        speak: Optional[Callable[[str], None]] = None,
        use_memory: bool = True,
    ):
        self.engines = engines or get_engines()
        self.tools = tools or get_tools()
        self.gate = gate or PermissionGate(mode=config.get("approval_mode", "ask"))
        self.max_steps = int(max_steps or config.get("max_steps", 12))
        self.verbose = verbose
        self.speak = speak
        self.use_memory = use_memory
        self.log = get_log()

    def _emit(self, text: str) -> None:
        if self.verbose:
            print(text)

    def run(self, goal: str) -> AgentOutcome:
        session = self.log.new_session()
        history: List[Dict[str, Any]] = []
        tools_used: List[str] = []
        denials: List[Dict[str, str]] = []
        engine_name = ""
        parse_retries = 0
        failures: Dict[str, int] = {}
        blocked: Dict[str, str] = {}

        try:
            preferred = config.get("engine", "auto")
            self.engines.select(preferred)
            engine_name = self.engines.active.name if self.engines.active else ""
        except EngineError as exc:
            message = f"no engine available:\n{exc}"
            self.log.record(session, goal, 0, "error", error=message)
            return AgentOutcome(False, message, 0, "", [], [], [], session, error=str(exc))

        self.log.record(session, goal, 0, "session_open", engine=engine_name, mode=self.gate.mode, max_steps=self.max_steps)
        self._emit(f"  engine {engine_name} | mode {self.gate.mode} | max {self.max_steps} steps")

        for step in range(1, self.max_steps + 1):
            messages = self._messages(goal, history, session, step)
            started = time.time()
            try:
                reply = self.engines.complete(messages, temperature=0.2, preferred=config.get("engine", "auto"))
            except EngineError as exc:
                self.log.record(session, goal, step, "error", error=str(exc))
                return AgentOutcome(False, f"engine failed at step {step}: {exc}", step, engine_name, tools_used, denials, history, session, error=str(exc))

            text = reply["text"]
            engine_name = reply["engine"]
            action, args, thought, parse_error = intelligence.parse_reply(text)
            self.log.record(session, goal, step, "llm_response", engine=engine_name, ms=round((time.time() - started) * 1000), action=action, thought=thought[:200], raw=text[:400])

            if parse_error:
                parse_retries += 1
                self._emit(f"  step {step}: {parse_error} - asking for strict JSON")
                history.append({"step": step, "action": "invalid", "args": {}, "observation": f"Your reply was not a valid JSON action ({parse_error}). Reply with one JSON object only."})
                if parse_retries > 2:
                    return AgentOutcome(False, "model never produced a valid action", step, engine_name, tools_used, denials, history, session, error="bad_protocol")
                continue

            parse_retries = 0
            self._emit(f"  step {step}: {thought[:110] or '(no reasoning given)'}" if thought else f"  step {step}: {action}")

            if action == intelligence.FINAL:
                message = str(args.get("message") or args.get("result") or "").strip() or "(the model returned an empty final message)"
                self._finish(session, goal, step, engine_name, history, True, message)
                if self.speak:
                    self.speak(message)
                return AgentOutcome(True, message, step, engine_name, tools_used, denials, history, session)

            tool_name = action
            if tool_name in blocked:
                observation = (
                    f"TOOL BLOCKED: {tool_name} already failed twice with \"{self._short(blocked[tool_name])}\". "
                    "That reason will not change, so the tool is closed for this run. Use a different tool, or "
                    'answer with {"thought": "...", "action": "final", "args": {"message": "what you found"}}.'
                )
                self.log.record(session, goal, step, "tool_blocked", tool=tool_name, reason=blocked[tool_name][:200])
                history.append({"step": step, "action": tool_name, "args": args, "observation": observation})
                self._emit(f"      -> {self._short(observation)}")
                continue

            signature = _signature(tool_name, args)
            repeats = sum(1 for entry in history if entry.get("signature") == signature)
            if repeats >= 2:
                observation = (
                    f"REPEAT BLOCKED: you already called {tool_name} with these exact arguments {repeats} times "
                    "and the result was the same each time. Do not call it again. Either use a different tool, or "
                    'answer with {"thought": "...", "action": "final", "args": {"message": "what you found"}}.'
                )
                self.log.record(session, goal, step, "repeat_blocked", tool=tool_name, repeats=repeats)
                history.append({"step": step, "action": tool_name, "args": args, "observation": observation, "signature": signature})
                self._emit(f"      -> {self._short(observation)}")
                continue

            observation = self._observe(tool_name, args, session, goal, step)
            if observation.startswith("DENIED"):
                denials.append({"step": str(step), "tool": tool_name, "reason": observation})
            else:
                tools_used.append(tool_name)
            if observation.startswith(("DENIED", "FAILED")):
                key = tool_name + "|" + observation[:120]
                failures[key] = failures.get(key, 0) + 1
                if failures[key] >= 2 and tool_name not in blocked:
                    blocked[tool_name] = observation
            history.append({"step": step, "action": tool_name, "args": args, "observation": observation, "signature": signature})
            self._emit(f"      -> {self._short(observation)}")

        salvaged = self._salvage(goal, history, session)
        summary = salvaged or (
            f"stopped after {self.max_steps} step{'s' if self.max_steps != 1 else ''} without a final answer. "
            f"Last observation: {self._short(history[-1]['observation']) if history else 'none'}"
        )
        self._finish(session, goal, self.max_steps, engine_name, history, False, summary)
        return AgentOutcome(
            False,
            summary,
            self.max_steps,
            engine_name,
            tools_used,
            denials,
            history,
            session,
            error="max_steps",
        )

    def _salvage(self, goal: str, history: List[Dict[str, Any]], session: str) -> str:
        """Out of steps is not out of information: ask for an answer instead of another action."""
        if not history:
            return ""
        messages = [
            {"role": "system", "content": intelligence.build_system_prompt("", "", str(config.WORKSPACE))},
            {
                "role": "user",
                "content": (
                    f"GOAL: {goal}\n\nTRANSCRIPT:\n{intelligence.history_block(history)}\n\n"
                    "You have no steps left and cannot call a tool. Reply in plain text with the best answer the "
                    "transcript supports, or name exactly what is still missing."
                ),
            },
        ]
        try:
            reply = self.engines.complete(messages, temperature=0.2, preferred=config.get("engine", "auto"))
        except EngineError as exc:
            self.log.record(session, goal, self.max_steps, "salvage_failed", error=str(exc)[:200])
            return ""

        text = str(reply.get("text", "")).strip()
        action, args, _thought, parse_error = intelligence.parse_reply(text)
        if not parse_error and action and action != intelligence.FINAL:
            self.log.record(session, goal, self.max_steps, "salvage", used=False, reason="still asked for a tool")
            return ""
        answer = str(args.get("message") or args.get("result") or "").strip() if action == intelligence.FINAL else text
        self.log.record(session, goal, self.max_steps, "salvage", used=bool(answer), chars=len(answer))
        return answer

    def _messages(self, goal: str, history: List[Dict[str, Any]], session: str, step: int = 1) -> List[Dict[str, str]]:
        memory = context_block(goal) if self.use_memory else ""
        system = intelligence.build_system_prompt(self.tools.prompt_block(), memory, str(config.WORKSPACE))
        remaining = max(1, self.max_steps - step + 1)
        pressure = (
            f"\n\nSTEPS LEFT: {remaining}. An observation that starts with OK already holds the data - if one of them "
            "answers the goal, stop looking and reply with action \"final\" containing that answer. "
            "Repeating an earlier call will not change its result."
            if remaining <= 3
            else ""
        )
        user = (
            f"GOAL: {goal}\n\n"
            f"TRANSCRIPT SO FAR:\n{intelligence.history_block(history)}\n\n"
            "Decide the single next action. Reply with one JSON object only." + pressure
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _observe(self, tool_name: str, args: Dict[str, Any], session: str, goal: str, step: int) -> str:
        tool = self.tools.get(tool_name)
        if tool is None:
            known = ", ".join(self.tools.names())
            return f"UNKNOWN TOOL: '{tool_name}' does not exist. Available: {known}"

        self.log.record(session, goal, step, "tool_call", tool=tool_name, args={k: str(v)[:120] for k, v in args.items()}, risk=tool.risk)
        started = time.time()
        result, reason = self.tools.call_gated(tool_name, args, self.gate)
        ms = round((time.time() - started) * 1000, 1)
        ok = bool(result.get("ok"))
        payload = {k: v for k, v in result.items() if k not in ("ok", "_ms", "_tool")}
        self.log.record(session, goal, step, "tool_result", tool=tool_name, ok=ok, ms=ms, decision=reason, error=str(result.get("error", ""))[:200], result_keys=sorted(payload)[:8])

        if not ok:
            head = "DENIED" if result.get("denied") else "FAILED"
            if head == "DENIED":
                return (
                    f"DENIED ({reason}): {result.get('error', 'no error reported')}. No approval can be collected in "
                    "this run, so write and exec actions are unavailable - use a read-only tool (read_file, list_dir, "
                    'search_content) or answer with {"action": "final", "args": {"message": "..."}}.'
                )
            return f"FAILED ({reason}): {result.get('error', 'no error reported')}"
        return f"OK: {format_observation(payload)}"

    def _short(self, text: str) -> str:
        flat = " ".join(str(text).split())
        return flat[:160] + ("..." if len(flat) > 160 else "")

    def _finish(self, session: str, goal: str, steps: int, engine: str, history: List[Dict[str, Any]], ok: bool, summary: str) -> None:
        self.log.record(session, goal, steps, "session_close", ok=ok, summary=summary[:300], engine=engine)
        if self.use_memory:
            get_store().log_task(goal, ok, summary, [h["action"] for h in history], steps, engine)


def _signature(action: str, args: Dict[str, Any]) -> str:
    """Same action + same arguments, so the loop can see it is about to repeat itself."""
    return action + "|" + json.dumps(args, sort_keys=True, default=str)[:400]


def format_observation(payload: Dict[str, Any], limit: int = 1400) -> str:
    """Compact the tool result into something a small model can still reason over."""
    for key in ("content", "stdout", "output", "text", "tree"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw:
            body = raw.strip()
            # Counts first: a small model answers "how many" from the numbers it sees before the text.
            scalars = [
                (k, v) for k, v in payload.items()
                if k != key and not k.startswith("_")
                and (isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) <= 60))
            ]
            numbers = ", ".join(f"{k}={v}" for k, v in scalars if isinstance(v, (int, float)) and not isinstance(v, bool))
            details = ", ".join(f"{k}={v}" for k, v in scalars if not isinstance(v, (int, float)) or isinstance(v, bool))
            facts = ", ".join(part for part in (numbers, details) if part)
            prefix = f"{facts} " if facts else ""
            return f"{prefix}{key}={body[:limit]}" + (f" [+{len(body) - limit} chars]" if len(body) > limit else "")
    text = ", ".join(f"{k}={v}" for k, v in payload.items())
    return text[:limit]
