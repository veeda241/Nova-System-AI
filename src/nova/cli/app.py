"""nova - command line entry point for the agentic OS."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import config, skills, voice
from .. import __version__
from ..agents import ReactAgent, answer, looks_like_action
from ..engine import EngineError, get_registry as engine_registry
from ..intelligence import validate_python
from ..learning import get_log
from ..memory import get_db, get_store
from ..security import PermissionGate, default_mode
from ..tools import get_registry as tool_registry
from . import ui

GLOBAL_FLAGS = ("engine", "mode", "workspace", "max_steps", "json", "quiet")


def _global_parser() -> argparse.ArgumentParser:
    """SUPPRESS defaults keep parent options from being overwritten by subparsers."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--engine", default=argparse.SUPPRESS, help="force an engine: ollama | hf | groq | gemini | openai")
    parser.add_argument("--mode", choices=["ask", "yolo", "deny"], default=argparse.SUPPRESS, help="permission mode (default: ask)")
    parser.add_argument("--yolo", action="store_const", const="yolo", dest="mode", default=argparse.SUPPRESS, help="shortcut for --mode yolo")
    parser.add_argument("--workspace", default=argparse.SUPPRESS, help="sandbox root for file and shell tools")
    parser.add_argument("--max-steps", type=int, default=argparse.SUPPRESS, help="agent step budget")
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="machine-readable output")
    parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help="print only the final answer")
    return parser


def build_parser() -> argparse.ArgumentParser:
    global_ = _global_parser()
    root = argparse.ArgumentParser(prog="nova", description="Nova - a CLI agentic operating system.", parents=[global_])
    root.add_argument("--version", action="version", version=f"nova {__version__}")
    root.epilog = "bare `nova` opens the interactive shell; `nova --help` lists every subcommand."
    sub = root.add_subparsers(dest="command")

    ask = sub.add_parser("ask", parents=[global_], help="one question, no tools")
    ask.add_argument("question", nargs="+")

    go = sub.add_parser("go", parents=[global_], help="run a goal with the tool-using agent")
    go.add_argument("goal", nargs="+")
    go.add_argument("--first-step", action="store_true", help="decide step 1 and stop")

    tools = sub.add_parser("tools", parents=[global_], help="inspect or invoke registered tools")
    tools.add_argument("action", nargs="?", choices=["list", "show", "call", "schema"], default="list")
    tools.add_argument("name", nargs="?", help="tool name")
    tools.add_argument("args", nargs="*", help="key=value pairs for call")

    engine = sub.add_parser("engine", parents=[global_], help="list, switch or smoke-test engines")
    engine.add_argument("action", nargs="?", choices=["list", "use", "test", "models"], default="list")
    engine.add_argument("rest", nargs="*")

    memory = sub.add_parser("memory", parents=[global_], help="facts, notes and task history")
    memory.add_argument("action", nargs="?", choices=["show", "set", "get", "del", "search", "note", "notes", "history", "stats"], default="show")
    memory.add_argument("args", nargs="*")

    skills_p = sub.add_parser("skills", parents=[global_], help="replayable step sequences")
    skills_p.add_argument("action", nargs="?", choices=["list", "show", "run", "add", "rm"], default="list")
    skills_p.add_argument("args", nargs="*")

    traces = sub.add_parser("traces", parents=[global_], help="what the agent actually did")
    traces.add_argument("action", nargs="?", choices=["stats", "recent", "session"], default="stats")
    traces.add_argument("args", nargs="*")

    sub.add_parser("doctor", parents=[global_], help="engine, dependency and sandbox health report")

    voice_p = sub.add_parser("voice", parents=[global_], help="optional speech in/out")
    voice_p.add_argument("action", nargs="?", choices=["status", "on", "off", "say", "listen"], default="status")
    voice_p.add_argument("text", nargs="*")

    conf = sub.add_parser("config", parents=[global_], help="read or write settings")
    conf.add_argument("action", nargs="?", choices=["show", "set", "paths"], default="show")
    conf.add_argument("args", nargs="*")

    val = sub.add_parser("validate", parents=[global_], help="AST-check a Python file")
    val.add_argument("path")

    sub.add_parser("chat", parents=[global_], help="interactive shell (same as bare `nova`)")
    return root


def normalise(args: argparse.Namespace) -> argparse.Namespace:
    for flag in GLOBAL_FLAGS:
        if flag == "max_steps":
            args.max_steps = getattr(args, "max_steps", None)
        elif flag in ("json", "quiet"):
            setattr(args, flag, bool(getattr(args, flag, False)))
        else:
            setattr(args, flag, getattr(args, flag, None))
    return args


def apply_globals(args: argparse.Namespace) -> None:
    config.load_env()
    if args.workspace:
        config.WORKSPACE = Path(args.workspace).expanduser().resolve()
    config.override("engine", args.engine)
    config.override("approval_mode", args.mode)
    config.override("max_steps", args.max_steps)
    config.ensure_dirs()


def make_gate(args: argparse.Namespace) -> PermissionGate:
    """--mode wins, then NOVA_YOLO=1, then the saved approval_mode."""
    return PermissionGate(mode=default_mode(args.mode))


def _pairs(raw: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in raw:
        if "=" not in item:
            continue
        key, _, value = item.partition("=")
        try:
            out[key.strip()] = json.loads(value)
        except ValueError:
            out[key.strip()] = value
    return out


def cmd_ask(args: argparse.Namespace) -> int:
    reply = answer(" ".join(args.question))
    if not reply.get("ok"):
        ui.fail(reply.get("error", "no answer"))
        ui.warn("run `nova doctor` to see why every engine was rejected")
        return 3
    if args.json:
        print(json.dumps(reply, indent=2))
    else:
        ui.heading("answer")
        ui.line(reply["text"])
        ui.line(f"\n  ({reply['engine']})")
    return 0


def cmd_go(args: argparse.Namespace) -> int:
    agent = ReactAgent(gate=make_gate(args), max_steps=args.max_steps, verbose=not args.quiet and not args.json)
    if args.first_step:
        agent.max_steps = 1
    outcome = agent.run(" ".join(args.goal))
    if args.json:
        print(json.dumps(outcome.as_dict(), indent=2, default=str))
    else:
        ui.heading("result" if outcome.ok else "stopped")
        ui.line(outcome.final)
        ui.line(f"\n  steps={outcome.steps} engine={outcome.engine} tools={', '.join(sorted(set(outcome.tools_used))) or 'none'}")
        if outcome.denials:
            ui.warn(f"{len(outcome.denials)} action(s) blocked by the permission gate")
    return 0 if outcome.ok else 1


def cmd_tools(args: argparse.Namespace) -> int:
    registry = tool_registry()
    if args.action == "list":
        ui.heading("tool registry")
        rows = registry.rows()
        columns = ["name", "risk", "available", "description"]
        floors = {"name": 16, "risk": 11, "available": 9}
        if any(row.get("reason") for row in rows):
            columns.insert(3, "reason")
            floors["reason"] = 12
        ui.kv(rows, columns, floors)
        ui.line(f"\n  {len(registry.available())} of {len(registry.tools)} ready | workspace {config.WORKSPACE} | mode {make_gate(args).mode}")
        return 0
    if args.action in ("show", "schema"):
        tool = registry.get(args.name or "")
        if tool is None:
            ui.fail(f"unknown tool '{args.name}' - try `nova tools list`")
            return 2
        payload = {"name": tool.name, "description": tool.description, "risk": tool.risk, "params": tool.params, "available": tool.available, "example": tool.example}
        if args.action == "schema" or args.json:
            print(json.dumps(payload, indent=2))
        else:
            ui.result(payload)
        return 0
    if args.action == "call":
        if not args.name:
            ui.fail("usage: nova tools call <name> key=value ...")
            return 2
        result, reason = registry.call_gated(args.name, _pairs(args.args), make_gate(args))
        ui.line(f"  gate: {reason}")
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            ui.result(result)
        return 0 if result.get("ok") else 1
    return 2


ENGINE_COLUMNS = ["name", "model", "available", "local", "priority", "active"]
ENGINE_FLOORS = {"name": 7, "model": 14, "available": 9, "local": 5, "priority": 8, "active": 6}


def show_engines(rows: List[Dict[str, Any]]) -> None:
    """Long setup hints would shatter a table, so they go underneath it as lines."""
    ui.kv(rows, [column for column in ENGINE_COLUMNS if column in rows[0]], ENGINE_FLOORS)
    for row in rows:
        if not row["available"]:
            ui.line(f"  {row['name']}: {row['reason']}")


def cmd_engine(args: argparse.Namespace) -> int:
    registry = engine_registry()
    if args.action == "list":
        ui.heading("engines (local first, then hosted)")
        show_engines(registry.status())
        return 0
    if args.action == "use":
        if not args.rest:
            ui.fail("usage: nova engine use <name>")
            return 2
        try:
            registry.select(args.rest[0])
        except EngineError as exc:
            ui.fail(str(exc))
            return 3
        config.save_settings({"engine": args.rest[0]})
        ui.ok(f"engine set to {args.rest[0]} ({registry.active.model})")
        return 0
    if args.action == "models":
        name = args.rest[0] if args.rest else str(config.get("engine", "auto"))
        try:
            payload = registry.models(name)
        except EngineError as exc:
            ui.fail(str(exc))
            return 3
        models = payload["models"]
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        ui.heading(f"{payload['engine']} models (current: {payload['current']})")
        for model in models:
            ui.line(f"  {model}")
        note = str(payload.get("note") or "")
        if note:
            ui.warn(f"  {note}")
        ui.line(f"\n  {len(models)} available - set one with `nova config set {payload['engine']}_model <name>`")
        return 0
    if args.action == "test":
        prompt = " ".join(args.rest) or "Reply with exactly: nova engine online"
        try:
            reply = registry.complete([{"role": "user", "content": prompt}], temperature=0.1, preferred=config.get("engine", "auto"))
        except EngineError as exc:
            ui.fail(str(exc))
            return 3
        ui.ok(f"{reply['engine']} round trip succeeded")
        ui.line("  " + reply["text"][:500])
        return 0
    return 2


def cmd_memory(args: argparse.Namespace) -> int:
    store, db = get_store(), get_db()
    action, rest = args.action, args.args

    if action == "show":
        ui.heading("facts")
        ui.kv([{"key": key, "value": value} for key, value in store.facts().items()], ["key", "value"])
        ui.heading("structured knowledge")
        ui.result(db.categories())
        ui.heading("stats")
        ui.result(store.stats())
        return 0
    if action == "set":
        if len(rest) < 2:
            ui.fail("usage: nova memory set <key> <value>")
            return 2
        ui.result(store.remember(rest[0], " ".join(rest[1:])), args.json)
        return 0
    if action == "get":
        if not rest:
            ui.fail("usage: nova memory get <key>")
            return 2
        ui.result(store.recall(rest[0]), args.json)
        return 0
    if action == "del":
        if not rest:
            ui.fail("usage: nova memory del <key>")
            return 2
        ui.result(store.forget(rest[0]), args.json)
        return 0
    if action == "search":
        if not rest:
            ui.fail("usage: nova memory search <query>")
            return 2
        ui.result(store.search(" ".join(rest)), args.json)
        return 0
    if action == "note":
        if len(rest) < 3:
            ui.fail("usage: nova memory note <category> <key> <value>")
            return 2
        ui.result(db.store(rest[0], rest[1], " ".join(rest[2:])), args.json)
        return 0
    if action == "notes":
        ui.result(db.retrieve(rest[0]) if rest else db.categories(), args.json)
        return 0
    if action == "history":
        ui.kv(compact_clock(store.tasks(int(rest[0]) if rest else 15)), ["ts", "ok", "goal", "steps", "engine", "summary"], {"ts": 8, "ok": 3, "goal": 22, "steps": 5, "engine": 7})
        return 0
    if action == "stats":
        ui.result({**store.stats(), "knowledge_rows": db.stats()["knowledge_rows"], "snippets": db.stats()["snippets"]}, args.json)
        return 0
    return 2


def cmd_skills(args: argparse.Namespace) -> int:
    action, rest = args.action, args.args
    if action == "list":
        ui.kv(skills.listing(), ["name", "description", "steps", "params", "origin"], {"name": 14, "description": 20, "steps": 5, "params": 8})
        return 0
    if action == "show":
        found = skills.get(rest[0]) if rest else None
        if found is None:
            ui.fail(f"usage: nova skills show <name> (see `nova skills list`)")
            return 2
        ui.result({"name": rest[0], **found}, args.json)
        return 0
    if action == "run":
        if not rest:
            ui.fail("usage: nova skills run <name> key=value ...")
            return 2
        result = skills.run(rest[0], make_gate(args), _pairs(rest[1:]))
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            ui.result(result)
        return 0 if result.get("ok") else 1
    if action == "add":
        if len(rest) < 3:
            ui.fail('usage: nova skills add <name> <description> <json-steps>')
            return 2
        try:
            steps = json.loads(" ".join(rest[2:]))
        except ValueError as exc:
            ui.fail(f"steps must be JSON: {exc}")
            return 2
        if not isinstance(steps, list):
            ui.fail("steps must be a JSON array of {action,args} objects")
            return 2
        ui.result(skills.add(rest[0], rest[1], steps), args.json)
        return 0
    if action == "rm":
        if not rest:
            ui.fail("usage: nova skills rm <name>")
            return 2
        ui.result(skills.remove(rest[0]), args.json)
        return 0
    return 2


def compact_clock(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ISO timestamps eat half a terminal; a clock reading is enough for recent work."""
    trimmed = []
    for row in rows:
        stamp = str(row.get("ts") or "")
        row = dict(row)
        if len(stamp) >= 19:
            row["ts"] = stamp[11:19]
        trimmed.append(row)
    return trimmed


def cmd_traces(args: argparse.Namespace) -> int:
    log = get_log()
    if args.action == "stats":
        payload = dict(log.stats())
        for key in ("most_used_tools", "tools_with_failures", "top_errors", "engines_used"):
            payload[key] = [f"{name} x{count}" for name, count in payload.get(key) or []]
        if args.json:
            print(json.dumps(payload, indent=2, default=str))
        else:
            ui.result(payload)
            ui.warn("traces are recorded for inspection and offline evaluation - Nova does not fine-tune a model from them")
        return 0
    if args.action == "session":
        if not args.args:
            ui.fail("usage: nova traces session <id>")
            return 2
        rows = log.read(limit=500, session=args.args[0])
    else:
        rows = log.read(limit=int(args.args[0]) if args.args else 25)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        ui.warn("no traces yet - run `nova go \"...\"` first")
        return 0
    rows = compact_clock(rows)
    columns = ["ts", "step", "event", "tool", "ok", "ms", "decision", "error"]
    floors = {"ts": 8, "step": 4, "event": 11, "tool": 14, "ok": 3, "ms": 5, "decision": 11}
    if not any(row.get("error") for row in rows):
        columns.remove("error")
    ui.kv(rows, columns, floors)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    registry = engine_registry()
    rows = registry.status()
    usable = [row for row in rows if row["available"]]
    ui.heading("engines")
    show_engines(rows)
    if not usable:
        ui.fail("no engine is reachable - Nova cannot think until one is configured")
        ui.line("    local : install Ollama, run `ollama serve`, then `ollama pull llama3.2`")
        ui.line("    hosted: put GEMINI_API_KEY or GROQ_API_KEY in .env (see .env.example)")

    blocked = [row for row in tool_registry().rows() if not row["available"]]
    if blocked:
        ui.heading("tools not ready")
        ui.kv(blocked, ["name", "risk", "reason"], {"name": 16, "risk": 11, "reason": 24})
    else:
        ui.heading("tools")
        ui.ok(f"{len(tool_registry().rows())} tools registered, all ready")

    ui.heading("voice (optional)")
    ui.result(voice.status())

    ui.heading("state")
    env_files = [str(path) for path in (config.NOVA_HOME / ".env", config.NOVA_HOME / "Config" / ".env", Path.cwd() / ".env") if path.is_file()]
    ui.result(
        {
            "home": str(config.NOVA_HOME),
            "workspace": str(config.WORKSPACE),
            "workspace_exists": config.WORKSPACE.is_dir(),
            "state_dir": str(config.STATE_DIR),
            "traces": str(config.TRACES_FILE),
            "engine_setting": config.get("engine"),
            "approval_mode": config.get("approval_mode"),
            "env_files": env_files or ["none - keys must be in the shell environment"],
        },
        args.json,
    )
    return 0 if usable else 3


def cmd_voice(args: argparse.Namespace) -> int:
    text = " ".join(args.text)
    if args.action == "status":
        ui.result(voice.status(), args.json)
        return 0
    if args.action == "on":
        ui.result(voice.set_enabled(True), args.json)
        return 0
    if args.action == "off":
        ui.result(voice.set_enabled(False), args.json)
        return 0
    if args.action == "say":
        if not text:
            ui.fail("usage: nova voice say <text>")
            return 2
        ui.result(voice.say(text), args.json)
        return 0
    if args.action == "listen":
        ui.result(voice.listen(), args.json)
        return 0
    return 2


def cmd_config(args: argparse.Namespace) -> int:
    if args.action == "paths":
        ui.result({"home": str(config.NOVA_HOME), "state": str(config.STATE_DIR), "workspace": str(config.WORKSPACE), "settings": str(config.SETTINGS_FILE)}, args.json)
        return 0
    if args.action == "set":
        if len(args.args) < 2:
            ui.fail("usage: nova config set <key> <value>")
            return 2
        try:
            parsed: Any = json.loads(" ".join(args.args[1:]))
        except ValueError:
            parsed = " ".join(args.args[1:])
        ui.result({"settings": config.save_settings({args.args[0]: parsed})}, args.json)
        return 0
    ui.result({"settings": config.load_settings()}, args.json)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        ui.fail(f"not found: {path}")
        return 2
    ui.result({"file": str(path), **validate_python(path.read_text(encoding="utf-8", errors="ignore"))}, args.json)
    return 0


HELP_TEXT = """
  plain text          a question gets a direct answer, an instruction runs as a goal
  /tools              tool registry            /engine <name>   switch engine
  /mode <ask|yolo|deny>  permission mode       /steps <n>       agent step budget
  /memory             facts + notes            /history         recent goals
  /skills             replayable sequences     /traces          last agent steps
  /doctor             engine & deps report     /workspace       sandbox root
  /say <text>         speak (voice on)         /listen          transcribe mic
  /quiet              toggle step output       /quit            leave
"""


def cmd_chat(args: argparse.Namespace) -> int:
    ui.banner(f"nova {__version__} | workspace {config.WORKSPACE}")
    gate = make_gate(args)
    agent = ReactAgent(gate=gate, max_steps=args.max_steps, verbose=not args.quiet)
    registry = engine_registry()
    try:
        registry.select(str(config.get("engine", "auto")))
        ui.line(f"  engine {registry.active.name} ({registry.active.model}) | mode {gate.mode} | steps {agent.max_steps}")
    except EngineError as exc:
        ui.warn(f"no engine ready:\n{exc}")
        ui.line("  type /doctor for detail, /quit to leave")

    if config.get("voice", "off") == "on":
        agent.speak = voice.say

    while True:
        try:
            prompt = input("\n  nova> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", ":q"):
            break

        if prompt.startswith("/"):
            if _slash(prompt, args, agent) == "quit":
                break
            continue

        if looks_like_action(prompt):
            outcome = agent.run(prompt)
            ui.heading("result" if outcome.ok else "stopped")
            ui.line(outcome.final)
            ui.line(f"  steps={outcome.steps} tools={', '.join(sorted(set(outcome.tools_used))) or 'none'}")
        else:
            reply = answer(prompt)
            if reply.get("ok"):
                ui.line(reply["text"])
            else:
                ui.fail(reply.get("error", "no answer"))

    ui.line("  bye")
    return 0


def _slash(prompt: str, args: argparse.Namespace, agent: ReactAgent) -> Optional[str]:
    parts = shlex.split(prompt)
    command, rest = parts[0].lower(), parts[1:]
    registry = engine_registry()

    if command in ("/quit", "/exit", "/q"):
        return "quit"
    if command == "/help":
        ui.line(HELP_TEXT)
    elif command == "/tools":
        args.action, args.name, args.args = "list", None, []
        cmd_tools(args)
    elif command == "/engine":
        if rest:
            try:
                registry.select(rest[0])
                config.save_settings({"engine": rest[0]})
                agent.engines = registry
                ui.ok(f"engine -> {rest[0]} ({registry.active.model})")
            except EngineError as exc:
                ui.fail(str(exc))
        else:
            show_engines(registry.status())
    elif command == "/mode":
        mode = rest[0] if rest else "ask"
        if mode not in ("ask", "yolo", "deny"):
            ui.fail("mode is ask | yolo | deny")
        else:
            agent.gate.mode = mode
            config.save_settings({"approval_mode": mode})
            ui.ok(f"approval mode -> {mode}")
    elif command == "/steps":
        try:
            agent.max_steps = max(1, int(rest[0]))
            ui.ok(f"max steps -> {agent.max_steps}")
        except (IndexError, ValueError):
            ui.fail("usage: /steps <n>")
    elif command == "/memory":
        ui.result(get_store().search(" ".join(rest)) if rest else {"stats": get_store().stats(), "facts": get_store().facts()})
    elif command == "/history":
        ui.kv(compact_clock(get_store().tasks(10)), ["ts", "ok", "goal", "steps", "engine"], {"ts": 8, "ok": 3, "goal": 22, "steps": 5, "engine": 7})
    elif command == "/skills":
        ui.kv(skills.listing(), ["name", "description", "steps", "params"], {"name": 14, "description": 20, "steps": 5, "params": 8})
    elif command == "/traces":
        ui.kv(compact_clock(get_log().read(15)), ["ts", "event", "tool", "ok", "ms", "decision"], {"ts": 8, "event": 11, "tool": 14, "ok": 3, "ms": 5})
    elif command == "/doctor":
        cmd_doctor(args)
    elif command == "/workspace":
        from ..tools import files

        ui.result(files.workspace_info())
    elif command == "/say":
        ui.result(voice.say(" ".join(rest)))
    elif command == "/listen":
        ui.result(voice.listen())
    elif command == "/voice":
        ui.result(voice.set_enabled(bool(rest and rest[0] == "on")))
    elif command == "/quiet":
        agent.verbose = not agent.verbose
        ui.ok(f"step output -> {'on' if agent.verbose else 'off'}")
    else:
        ui.fail(f"unknown command {command} - /help")
    return None


DISPATCH: Dict[str, Any] = {
    "ask": cmd_ask,
    "go": cmd_go,
    "chat": cmd_chat,
    "tools": cmd_tools,
    "engine": cmd_engine,
    "memory": cmd_memory,
    "skills": cmd_skills,
    "traces": cmd_traces,
    "doctor": cmd_doctor,
    "voice": cmd_voice,
    "config": cmd_config,
    "validate": cmd_validate,
}


def main(argv: Optional[List[str]] = None) -> int:
    ui.force_utf8()
    parser = build_parser()
    args = normalise(parser.parse_args(argv))
    apply_globals(args)
    command = getattr(args, "command", None)
    handler = DISPATCH.get(command, cmd_chat if command is None else None)
    if handler is None:
        parser.print_help()
        return 2
    try:
        return handler(args)
    except KeyboardInterrupt:
        ui.warn("interrupted")
        return 130
    except EngineError as exc:
        ui.fail(str(exc))
        return 3


if __name__ == "__main__":
    sys.exit(main())
