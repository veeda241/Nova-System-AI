"""Agents primitive: a direct-answer path and the tool-using ReAct path."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .. import config, intelligence
from ..engine import EngineError, get_registry as get_engines
from ..memory import context_block
from .react import AgentOutcome, ReactAgent

__all__ = ["ReactAgent", "AgentOutcome", "answer", "looks_like_action"]

ACTION_CUES = (
    "create", "make", "write", "delete", "rename", "move", "copy", "run", "execute", "list", "find",
    "search for", "open", "install", "fix", "build", "check", "count", "organise", "organize", "clean",
    "summarise the file", "summarize the file", "show me", "go to", "add", "update", "generate",
)


def answer(
    prompt: str,
    engines: Optional[Any] = None,
    use_memory: bool = True,
    temperature: float = 0.4,
    system: Optional[str] = None,
) -> Dict[str, Any]:
    """Single-shot, tool-free completion - this is what `nova ask` uses."""
    reg = engines or get_engines()
    memory = context_block(prompt) if use_memory else ""
    chunks = [system or intelligence.PERSONA]
    chunks.append("This is a direct question. Answer it; you are not calling tools in this turn.")
    if memory:
        chunks.append(memory)
    messages = [{"role": "system", "content": "\n\n".join(chunks)}, {"role": "user", "content": prompt}]
    try:
        reply = reg.complete(messages, temperature=temperature, preferred=config.get("engine", "auto"))
    except EngineError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "engine": reply["engine"], "text": reply["text"]}


def looks_like_action(text: str) -> bool:
    low = text.strip().lower()
    if low.endswith("?"):
        return False
    return any(low.startswith(cue) or f" {cue} " in f" {low} " for cue in ACTION_CUES)
