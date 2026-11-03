"""The ReAct agent: think, call one tool, observe the real result, repeat."""

from __future__ import annotations

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
            messages = self._messages(goal, history, session)
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
            observation = self._observe(tool_name, args, session, goal, step)
            if observation.startswith("DENIED"):
                denials.append({"step": str(step), "tool": tool_name, "reason": observation})
            else:
                tools_used.append(tool_name)
            history.append({"step": step, "action": tool_name, "args": args, "observation": observation})
            self._emit(f"      -> {self._short(observation)}")

        self._finish(session, goal, len(history), engine_name, history, False, "step budget exhausted")
        return AgentOutcome(
            False,
            f"stopped after {self.max_steps} step{'s' if self.max_steps != 1 else ''} without a final answer. Last observation: {self._short(history[-1]['observation']) if history else 'none'}",
            self.max_steps,
            engine_name,
            tools_used,
            denials,
            history,
            session,
            error="max_steps",
        )

    def _messages(self, goal: str, history: List[Dict[str, Any]], session: str) -> List[Dict[str, str]]:
        memory = context_block(goal) if self.use_memory else ""
        system = intelligence.build_system_prompt(self.tools.prompt_block(), memory, str(config.WORKSPACE))
        user = (
            f"GOAL: {goal}\n\n"
            f"TRANSCRIPT SO FAR:\n{intelligence.history_block(history)}\n\n"
            "Decide the single next action. Reply with one JSON object only."
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
            return f"{head} ({reason}): {result.get('error', 'no error reported')}"
        return f"OK: {format_observation(payload)}"

    def _short(self, text: str) -> str:
        flat = " ".join(str(text).split())
        return flat[:160] + ("..." if len(flat) > 160 else "")

    def _finish(self, session: str, goal: str, steps: int, engine: str, history: List[Dict[str, Any]], ok: bool, summary: str) -> None:
        self.log.record(session, goal, steps, "session_close", ok=ok, summary=summary[:300], engine=engine)
        if self.use_memory:
            get_store().log_task(goal, ok, summary, [h["action"] for h in history], steps, engine)


def format_observation(payload: Dict[str, Any], limit: int = 1400) -> str:
    """Compact the tool result into something a small model can still reason over."""
    for key in ("content", "stdout", "output", "text", "tree"):
        if isinstance(payload.get(key), str) and payload[key]:
            body = payload[key].strip()
            return f"{key}={body[:limit]}" + (f" [+{len(body) - limit} chars]" if len(body) > limit else "")
    text = ", ".join(f"{k}={v}" for k, v in payload.items())
    return text[:limit]
