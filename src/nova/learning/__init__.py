"""Learning primitive: every agent step is written to a JSONL trace log.

Traces are for inspection and offline evaluation (`nova traces`). Nova does not
fine-tune anything from them - that would be a claim this code cannot back up.
"""

from __future__ import annotations

import json
import time
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import config


class TraceLog:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or config.TRACES_FILE)

    def new_session(self) -> str:
        return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]

    def record(self, session: str, goal: str, step: int, event: str, **fields: Any) -> Dict[str, Any]:
        row = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "epoch": time.time(),
            "session": session,
            "goal": goal[:200],
            "step": step,
            "event": event,
        }
        row.update({k: _shrink(v) for k, v in fields.items()})
        config.ensure_dirs()
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, default=str) + "\n")
        return row

    def read(self, limit: int = 200, session: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if session and row.get("session") != session:
                continue
            rows.append(row)
        return rows[-int(limit) :]

    def stats(self) -> Dict[str, Any]:
        rows = self.read(limit=100_000)
        calls = [r for r in rows if r.get("event") == "tool_call"]
        outcomes = [r for r in rows if r.get("event") == "tool_result"]
        latencies = [r.get("ms", 0) for r in outcomes if isinstance(r.get("ms"), (int, float))]
        errors = Counter(str(r.get("error", ""))[:90] for r in outcomes if r.get("ok") is False)
        per_tool = Counter(str(r.get("tool")) for r in calls)
        failed = Counter(str(r.get("tool")) for r in outcomes if r.get("ok") is False)
        engine = Counter(str(r.get("engine")) for r in rows if r.get("event") == "llm_response")
        return {
            "rows": len(rows),
            "sessions": len({r.get("session") for r in rows}),
            "tool_calls": len(calls),
            "tool_success_rate": round((len(outcomes) - sum(failed.values())) / len(outcomes) * 100, 1) if outcomes else None,
            "avg_tool_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "slowest_tool_ms": max(latencies) if latencies else None,
            "most_used_tools": per_tool.most_common(5),
            "tools_with_failures": failed.most_common(5),
            "top_errors": [(k, n) for k, n in errors.most_common(5) if k],
            "engines_used": engine.most_common(),
        }


def _shrink(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 800:
        return value[:800] + "...[truncated]"
    if isinstance(value, dict):
        return {k: _shrink(v) for k, v in value.items()}
    return value


_log: Optional[TraceLog] = None


def get_log() -> TraceLog:
    global _log
    if _log is None:
        _log = TraceLog()
    return _log
