"""Skills: named, replayable step sequences. Runs deterministically, no LLM needed."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config
from .security import PermissionGate
from .tools import get_registry

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


def add(name: str, description: str, steps: List[Dict[str, Any]], params: Optional[List[str]] = None) -> Dict[str, Any]:
    if not steps:
        return {"ok": False, "error": "a skill needs at least one step"}
    skills = load()
    skills[name] = {
        "description": description,
        "created": datetime.now().isoformat(timespec="seconds"),
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


def run(name: str, gate: PermissionGate, values: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    skill = get(name)
    if skill is None:
        return {"ok": False, "error": f"no skill called '{name}'", "known": sorted(load())}

    values = dict(values or {})
    missing = [p for p in skill.get("params", []) if p not in values]
    if missing:
        return {"ok": False, "error": f"skill '{name}' needs {' '.join(f'{m}=<value>' for m in missing)}"}

    registry = get_registry()
    results: List[Dict[str, Any]] = []
    for index, step in enumerate(skill.get("steps", []), 1):
        action = step.get("action")
        args = _fill(step.get("args", {}), values)
        result, reason = registry.call_gated(action, args, gate)
        results.append({"step": index, "action": action, "ok": bool(result.get("ok")), "detail": _brief(result), "decision": reason})
        if not result.get("ok"):
            return {"ok": False, "skill": name, "failed_at": index, "results": results}
    return {"ok": True, "skill": name, "results": results}


def _fill(value: Any, values: Dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, item in values.items():
            value = value.replace("{" + key + "}", str(item))
        return value
    if isinstance(value, dict):
        return {k: _fill(v, values) for k, v in value.items()}
    return value


def _brief(result: Dict[str, Any]) -> str:
    if not result.get("ok"):
        return str(result.get("error", ""))[:160]
    keep = {k: v for k, v in result.items() if k not in ("ok", "_ms", "_tool")}
    return json.dumps(keep, default=str)[:220]
