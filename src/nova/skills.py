"""Skills: named, replayable step sequences. Deterministic steps need no LLM; `think` steps do."""

from __future__ import annotations

import json
import re
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config
from .security import PermissionGate
from .tools import get_registry

MODEL_STEP = "think"
STEP_OUTPUT_LIMIT = 1500

# OpenJarvis names -> Nova names. Everything here has been checked against the registry params.
TOOL_ALIASES = {
    "shell_exec": "run_command",
    "file_read": "read_file",
    "file_write": "write_file",
    "memory_search": "search_memory",
    "memory_store": "remember_fact",
    "code_interpreter": "run_python",
    "think": MODEL_STEP,
    "llm_call": MODEL_STEP,
}
ARG_ALIASES = {
    "memory_store": {"content": "value", "metadata": "key"},
    MODEL_STEP: {"thought": "prompt"},
}
NO_NOVA_EQUIVALENT = {
    "memory_index": "Nova notes are stored per key with store_note(category, key, value); this step indexes a whole directory",
    "web_search": "Nova has no web search tool",
    "http_request": "Nova has no web fetch tool",
    "pdf_extract": "Nova has no PDF text extraction tool",
}

# These binaries do not exist in the cmd.exe shell run_command spawns on Windows.
POSIX_ONLY = ("find ", "mkdir -p", "md5sum", "sha256sum", "file --mime-type", "date +", "head -", "tar czf")

SEED_SKILLS: Dict[str, Dict[str, Any]] = {
    "workspace_audit": {
        "description": "Report where the workspace is, how big it is, and which engines are up.",
        "created": "seed",
        "steps": [
            {"action": "workspace_info", "args": {}},
            {"action": "system_info", "args": {}},
            {"action": "engine_status", "args": {}},
        ],
    },
    "fresh_note": {
        "description": "Create notes/<name>.md and remember that it exists.",
        "created": "seed",
        "params": ["name"],
        "steps": [
            {"action": "write_file", "args": {"path": "notes/{name}.md", "content": "# {name}\n\n"}},
            {"action": "remember_fact", "args": {"key": "note:{name}", "value": "notes/{name}.md"}},
        ],
    },
}


def _file() -> Path:
    config.ensure_dirs()
    return Path(config.SKILLS_FILE)


def load() -> Dict[str, Dict[str, Any]]:
    path = _file()
    skills: Dict[str, Dict[str, Any]] = dict(SEED_SKILLS)
    if path.is_file():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                skills.update(stored)
        except (OSError, ValueError):
            pass
    return skills


def save(skills: Dict[str, Dict[str, Any]]) -> None:
    _file().write_text(json.dumps(skills, indent=2, default=str), encoding="utf-8")


def get(name: str) -> Optional[Dict[str, Any]]:
    return load().get(name)


def add(name: str, description: str, steps: List[Dict[str, Any]], params: Optional[List[str]] = None, origin: str = "") -> Dict[str, Any]:
    if not steps:
        return {"ok": False, "error": "a skill needs at least one step"}
    skills = load()
    skills[name] = {
        "description": description,
        "created": origin or datetime.now().isoformat(timespec="seconds"),
        "steps": steps,
        **({"params": params} if params else {}),
    }
    save(skills)
    return {"ok": True, "name": name, "steps": len(steps)}


def remove(name: str) -> Dict[str, Any]:
    skills = load()
    if name in skills:
        del skills[name]
        save(skills)
        return {"ok": True, "removed": name}
    return {"ok": False, "error": f"no skill called '{name}'"}


def listing() -> List[Dict[str, Any]]:
    return [
        {"name": name, "description": skill.get("description", ""), "steps": len(skill.get("steps", [])), "params": skill.get("params", []), "origin": skill.get("created", "")}
        for name, skill in sorted(load().items())
    ]


def run(name: str, gate: PermissionGate, values: Optional[Dict[str, str]] = None, engines: Optional[Any] = None) -> Dict[str, Any]:
    skill = get(name)
    if skill is None:
        return {"ok": False, "error": f"no skill called '{name}'", "known": sorted(load())}

    scope = dict(values or {})
    missing = [p for p in skill.get("params", []) if p not in scope]
    if missing:
        return {"ok": False, "error": f"skill '{name}' needs {' '.join(f'{m}=<value>' for m in missing)}"}

    registry = get_registry()
    results: List[Dict[str, Any]] = []
    for index, step in enumerate(skill.get("steps", []), 1):
        action = step.get("action")
        args = _fill(step.get("args", {}), scope)
        if action == MODEL_STEP:
            result = think(str(args.get("prompt", "")), engines)
            reason = "model"
        else:
            result, reason = registry.call_gated(action, args, gate)
        ok = bool(result.get("ok"))
        row = {"step": index, "action": action, "ok": ok, "detail": _brief(result), "decision": reason}
        if result.get("engine"):
            row["engine"] = result["engine"]
        results.append(row)
        if not ok:
            return {
                "ok": False,
                "skill": name,
                "failed_at": index,
                "error": f"{action} failed at step {index}: {result.get('error', 'no error reported')}",
                "results": results,
            }
        scope.setdefault(step.get("output_key") or action, _thread(result))
    return {"ok": True, "skill": name, "results": results}


def think(prompt: str, engines: Optional[Any] = None) -> Dict[str, Any]:
    """One model call inside a skill: judgement a fixed step list cannot do."""
    if not prompt.strip():
        return {"ok": False, "error": "a think step needs args.prompt"}
    from . import intelligence
    from .engine import EngineError, get_registry as get_engines

    try:
        reply = (engines or get_engines()).complete(
            [{"role": "system", "content": intelligence.PERSONA}, {"role": "user", "content": prompt}],
            temperature=0.3,
            preferred=config.get("engine", "auto"),
        )
    except EngineError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "engine": reply["engine"], "text": reply["text"]}


def _fill(value: Any, values: Dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, item in values.items():
            value = value.replace("{" + key + "}", str(item))
        return value
    if isinstance(value, dict):
        return {k: _fill(v, values) for k, v in value.items()}
    return value


def _thread(result: Dict[str, Any]) -> str:
    """What the next step sees when it names this step's output_key."""
    body = result["text"] if isinstance(result.get("text"), str) else json.dumps(
        {k: v for k, v in result.items() if k not in ("ok", "_ms", "_tool")}, default=str
    )
    return body[:STEP_OUTPUT_LIMIT] + ("[...clipped]" if len(body) > STEP_OUTPUT_LIMIT else "")


def _brief(result: Dict[str, Any]) -> str:
    if not result.get("ok"):
        return " ".join(str(result.get("error", "")).split())[:500]
    keep = {k: v for k, v in result.items() if k not in ("ok", "_ms", "_tool")}
    return json.dumps(keep, default=str)[:220]


def _placeholders(rendered: str, output_keys: List[str]) -> List[str]:
    named = set(re.findall(r"\{(\w+)\}", rendered))
    return sorted(named - set(output_keys))


def parse_pack(path: Path | str) -> Dict[str, Any]:
    """Read an OpenJarvis skill TOML into Nova's step format, listing every reason it cannot run."""
    skill = tomllib.loads(Path(path).read_text(encoding="utf-8")).get("skill", {})
    registry = get_registry()
    steps: List[Dict[str, Any]] = []
    problems: List[str] = []
    output_keys = [str(step["output_key"]) for step in skill.get("steps", []) if step.get("output_key")]

    for index, step in enumerate(skill.get("steps", []), 1):
        source = str(step.get("tool_name", ""))
        try:
            args = json.loads(step.get("arguments_template", "{}"))
        except ValueError as exc:
            problems.append(f"step {index}: arguments_template is not valid JSON ({exc})")
            continue
        if source in NO_NOVA_EQUIVALENT:
            problems.append(f"step {index} ({source}): {NO_NOVA_EQUIVALENT[source]}")
            continue
        target = TOOL_ALIASES.get(source)
        if target is None:
            problems.append(f"step {index}: Nova knows no tool called '{source}'")
            continue
        renames = ARG_ALIASES.get(source, {})
        args = {renames.get(key, key): value for key, value in args.items()}
        if target == MODEL_STEP:
            args = {"prompt": str(args.get("prompt", ""))}
        else:
            tool = registry.get(target)
            extra = sorted(set(args) - set(tool.params))
            if extra:
                problems.append(f"step {index}: {target} takes no {', '.join(extra)} (it takes {', '.join(tool.params) or 'nothing'})")
                continue
            missing = sorted(p for p in tool.required if p not in args)
            if missing:
                problems.append(f"step {index}: {target} is never given {', '.join(missing)}")
                continue
        command = args.get("command")
        if isinstance(command, str):
            posix = sorted({hint.strip() for hint in POSIX_ONLY if hint in command})
            if posix:
                problems.append(f"step {index}: run_command cannot do {', '.join(posix)} on Windows")
                continue
        entry: Dict[str, Any] = {"action": target, "args": args}
        if step.get("output_key"):
            entry["output_key"] = str(step["output_key"])
        steps.append(entry)

    rendered = json.dumps([s["args"] for s in steps])
    return {
        "name": str(skill.get("name", Path(path).stem)),
        "description": str(skill.get("description", "")),
        "steps": steps,
        "params": _placeholders(rendered, output_keys),
        "problems": problems,
        "origin": f"imported {skill.get('author', '?')}@{skill.get('version', '?')}",
    }


def import_pack(path: Path | str) -> Dict[str, Any]:
    """Import one pack, or refuse it with the exact blockers. Nothing is silently dropped."""
    parsed = parse_pack(path)
    if parsed["problems"]:
        return {"ok": False, "name": parsed["name"], "refused": parsed["problems"]}
    if not parsed["steps"]:
        return {"ok": False, "name": parsed["name"], "refused": ["the pack had no steps"]}
    added = add(parsed["name"], parsed["description"], parsed["steps"], parsed["params"], origin=parsed["origin"])
    return {**added, "params": parsed["params"]}


def import_dir(path: Path | str) -> Dict[str, Any]:
    imported, refused = [], {}
    for toml_path in sorted(Path(path).glob("*.toml")):
        outcome = import_pack(toml_path)
        if outcome.get("ok"):
            imported.append(outcome["name"])
        else:
            refused[outcome["name"]] = outcome.get("refused", ["unreadable"])
    return {"ok": bool(imported), "imported": imported, "refused": refused}
