"""Persistent facts and task history - plain JSON, no hidden magic."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import config


class MemoryStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or config.MEMORY_FILE)

    def _load(self) -> Dict[str, Any]:
        if not self.path.is_file():
            return {"facts": {}, "tasks": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"facts": {}, "tasks": []}
        data.setdefault("facts", {})
        data.setdefault("tasks", [])
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        config.ensure_dirs()
        self.path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def remember(self, key: str, value: Any) -> Dict[str, Any]:
        data = self._load()
        data["facts"][key.strip()] = {"value": value, "ts": datetime.now().isoformat(timespec="seconds")}
        self._save(data)
        return {"ok": True, "key": key, "value": value, "total_facts": len(data["facts"])}

    def recall(self, key: str) -> Dict[str, Any]:
        data = self._load()
        hit = data["facts"].get(key.strip())
        if not hit:
            return {"ok": False, "error": f"no fact named '{key}'", "similar": self._fuzzy(key, data)[:5]}
        return {"ok": True, "key": key, "value": hit["value"], "stored_at": hit.get("ts")}

    def facts(self) -> Dict[str, Any]:
        return {k: v["value"] for k, v in self._load()["facts"].items()}

    def forget(self, key: str) -> Dict[str, Any]:
        data = self._load()
        if key.strip() in data["facts"]:
            del data["facts"][key.strip()]
            self._save(data)
            return {"ok": True, "forgotten": key}
        return {"ok": False, "error": f"no fact named '{key}'"}

    def search(self, query: str) -> Dict[str, Any]:
        data = self._load()
        facts = [{"key": k, "value": v["value"]} for k, v in data["facts"].items() if query.lower() in json.dumps(v, default=str).lower() or query.lower() in k.lower()]
        tasks = [t for t in data["tasks"] if query.lower() in json.dumps(t, default=str).lower()][:10]
        return {"ok": True, "query": query, "facts": facts[:20], "tasks": tasks}

    def _fuzzy(self, key: str, data: Dict[str, Any]) -> List[str]:
        low = key.lower()
        return [k for k in data["facts"] if low in k.lower() or any(part in k.lower() for part in low.split())]

    def log_task(self, goal: str, ok: bool, summary: str, tools: List[str], steps: int, engine: str) -> Dict[str, Any]:
        data = self._load()
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "goal": goal[:300],
            "ok": bool(ok),
            "summary": summary[:400],
            "tools": sorted(set(tools)),
            "steps": steps,
            "engine": engine,
        }
        data["tasks"].append(entry)
        data["tasks"] = data["tasks"][-500:]
        self._save(data)
        return {"ok": True, **entry}

    def tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self._load()["tasks"]))[: int(limit)]

    def stats(self) -> Dict[str, Any]:
        data = self._load()
        tasks = data["tasks"]
        done = [t for t in tasks if t.get("ok")]
        return {
            "facts": len(data["facts"]),
            "tasks": len(tasks),
            "task_success_rate": round(len(done) / len(tasks) * 100, 1) if tasks else None,
            "path": str(self.path),
        }


_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
