"""Tools primitive: one registry, risk-labelled, dependency-aware, gated on call."""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..security import DESTRUCTIVE, EXEC, READ, WRITE, PermissionGate
from . import files, shell, system as system_tools

__all__ = ["Tool", "Registry", "get_registry", "register", "DESTRUCTIVE", "EXEC", "READ", "WRITE"]


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Dict[str, Any]]
    params: Dict[str, str] = field(default_factory=dict)
    risk: str = READ
    requires: Tuple[str, ...] = ()
    example: str = ""

    @property
    def available(self) -> bool:
        return all(_has(module) for module in self.requires)

    def unavailable_reason(self) -> str:
        missing = [m for m in self.requires if not _has(m)]
        return f"needs `pip install {missing[0]}`" if missing else ""

    def signature(self) -> str:
        if not self.params:
            return f"{self.name}()"
        args = ", ".join(f"{k}={_default(v)}" for k, v in self.params.items())
        return f"{self.name}({args})"

    def prompt_line(self) -> str:
        return f"- {self.signature()} [{self.risk}] {self.description} | args: {', '.join(self.params) or 'none'}"


def _default(type_name: str) -> str:
    return {"int": "0", "bool": "false", "list": "[]"}.get(type_name, "...")


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


class Registry:
    def __init__(self) -> None:
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self.tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def names(self) -> List[str]:
        return sorted(self.tools)

    def available(self) -> List[Tool]:
        return [t for t in sorted(self.tools.values(), key=lambda t: t.name) if t.available]

    def rows(self) -> List[Dict[str, Any]]:
        out = []
        for tool in sorted(self.tools.values(), key=lambda t: (t.risk, t.name)):
            out.append(
                {
                    "name": tool.name,
                    "risk": tool.risk,
                    "available": tool.available,
                    "reason": tool.unavailable_reason(),
                    "description": tool.description,
                    "params": tool.params,
                }
            )
        return out

    def prompt_block(self) -> str:
        lines = [t.prompt_line() for t in self.available()]
        return "\n".join(lines)

    def call(self, name: str, args: Optional[Dict[str, Any]] = None, gate: Optional[PermissionGate] = None) -> Dict[str, Any]:
        args = dict(args or {})
        tool = self.get(name)
        if tool is None:
            return {"ok": False, "error": f"unknown tool '{name}'", "known": self.names()}
        if not tool.available:
            return {"ok": False, "error": f"tool '{name}' is unavailable: {tool.unavailable_reason()}"}

        missing = [p for p in tool.params if p not in args and p not in ("path", "pattern", "query", "cwd", "limit", "timeout", "recursive", "append", "max_bytes", "max_files", "allow_outside")]
        if missing:
            return {"ok": False, "error": f"{name} is missing argument(s): {', '.join(missing)}"}

        started = time.time()
        try:
            result = tool.handler(**args)
        except TypeError as exc:
            return {"ok": False, "error": f"bad arguments for {name}: {exc}"}
        except Exception as exc:
            return {"ok": False, "error": f"{name} raised {exc.__class__.__name__}: {exc}"}
        if not isinstance(result, dict):
            result = {"ok": True, "result": result}
        result.setdefault("ok", True)
        result["_ms"] = round((time.time() - started) * 1000, 1)
        result["_tool"] = name
        return result

    def call_gated(self, name: str, args: Dict[str, Any], gate: PermissionGate) -> Tuple[Dict[str, Any], str]:
        """Returns (result, decision_reason). Denials never reach the handler."""
        tool = self.get(name)
        if tool is None:
            return {"ok": False, "error": f"unknown tool '{name}'"}, "unknown"
        summary = gate.summarize(name, args or {})
        decision = gate.review(name, tool.risk, args or {}, summary)
        if not decision.allowed:
            return {"ok": False, "error": f"action not performed: {decision.reason}", "denied": True}, decision.reason
        result = self.call(name, args)
        return result, decision.reason


_registry: Optional[Registry] = None


def _memory_tools() -> List[Tool]:
    from ..memory import get_db, get_store

    store, db = get_store(), get_db()
    return [
        Tool("remember_fact", "Store a durable key/value fact for later sessions.", store.remember, {"key": "str", "value": "str"}, WRITE, example='{"action":"remember_fact","args":{"key":"wifi","value":"LabNet"}}'),
        Tool("recall_fact", "Fetch a stored fact by key.", store.recall, {"key": "str"}, READ),
        Tool("search_memory", "Search stored facts and past task history.", store.search, {"query": "str"}, READ),
        Tool("store_note", "Save structured knowledge under category/key.", db.store, {"category": "str", "key": "str", "value": "str"}, WRITE),
        Tool("search_notes", "Full scan of SQLite knowledge for a substring.", db.search, {"query": "str"}, READ),
        Tool("log_snippet", "Save a reusable code snippet by name.", db.save_snippet, {"name": "str", "code": "str"}, WRITE),
    ]


def build_registry() -> Registry:
    reg = Registry()
    for tool in [
        Tool("list_dir", "List a directory in the workspace; recursive=true to walk.", files.list_dir, {"path": "str", "recursive": "bool"}, READ, example='{"action":"list_dir","args":{"path":"."}}'),
        Tool("read_file", "Read a text file (workspace unless allow_outside).", files.read_file, {"path": "str"}, READ, example='{"action":"read_file","args":{"path":"notes.md"}}'),
        Tool("find_files", "Glob filenames anywhere under a path.", files.find_files, {"pattern": "str", "path": "str"}, READ),
        Tool("search_content", "Grep for a string across files.", files.search_content, {"query": "str", "path": "str"}, READ),
        Tool("workspace_info", "Report workspace root, file count and size.", files.workspace_info, {}, READ),
        Tool("system_info", "Host OS, CPU, memory, disk and paths.", system_tools.system_info, {}, READ, ("psutil",)),
        Tool("top_processes", "Most CPU-active processes.", system_tools.top_processes, {"limit": "int"}, READ, ("psutil",)),
        Tool("engine_status", "Which model engines are usable right now.", system_tools.environment, {}, READ),
        Tool("write_file", "Create or overwrite a file in the workspace.", files.write_file, {"path": "str", "content": "str", "append": "bool"}, WRITE, example='{"action":"write_file","args":{"path":"out.txt","content":"hello"}}'),
        Tool("make_dir", "Create a directory.", files.make_dir, {"path": "str"}, WRITE),
        Tool("move_path", "Move or rename within the workspace.", files.move_path, {"src": "str", "dst": "str"}, WRITE),
        Tool("delete_path", "Delete a file or directory tree.", files.delete_path, {"path": "str"}, DESTRUCTIVE),
        Tool("run_command", "Run a shell command in the workspace.", shell.run_command, {"command": "str", "timeout": "int"}, EXEC, example='{"action":"run_command","args":{"command":"dir"}}'),
        Tool("run_python", "Execute Python code and capture output.", shell.run_python, {"code": "str", "timeout": "int"}, EXEC),
        Tool("run_python_file", "Run a .py file from the workspace.", shell.run_python_file, {"path": "str"}, EXEC),
        *_memory_tools(),
    ]:
        reg.register(tool)
    return reg


def get_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = build_registry()
    return _registry
