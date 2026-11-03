"""Structured long-term memory: SQLite categories, notes and code snippets."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    updated_at TEXT,
    UNIQUE(category, key)
);
CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    language TEXT,
    code TEXT,
    description TEXT
);
"""


class KnowledgeDB:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or config.KNOWLEDGE_DB)
        config.ensure_dirs()
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def store(self, category: str, key: str, value: Any) -> Dict[str, Any]:
        payload = value if isinstance(value, str) else json.dumps(value, default=str)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO knowledge (category, key, value, updated_at) VALUES (?,?,?,datetime('now'))",
                (category.strip().lower(), key.strip(), payload),
            )
        return {"ok": True, "category": category, "key": key}

    def retrieve(self, category: str, key: Optional[str] = None) -> Dict[str, Any]:
        with closing(self._connect()) as conn:
            if key:
                row = conn.execute("SELECT value FROM knowledge WHERE category=? AND key=?", (category.strip().lower(), key)).fetchone()
                if not row:
                    return {"ok": False, "error": f"nothing stored under {category}/{key}"}
                return {"ok": True, "value": _decode(row["value"])}
            rows = conn.execute("SELECT key, value FROM knowledge WHERE category=? ORDER BY updated_at DESC", (category.strip().lower(),)).fetchall()
        if not rows:
            return {"ok": False, "error": f"category '{category}' is empty"}
        return {"ok": True, "category": category, "entries": {r["key"]: _decode(r["value"]) for r in rows}}

    def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT category, key, value, updated_at FROM knowledge WHERE key LIKE ? OR value LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", int(limit)),
            ).fetchall()
        return {"ok": True, "query": query, "count": len(rows), "matches": [dict(r) for r in rows]}

    def categories(self) -> Dict[str, Any]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT category, COUNT(*) AS n FROM knowledge GROUP BY category ORDER BY category").fetchall()
        return {"ok": True, "categories": {r["category"]: r["n"] for r in rows}}

    def save_snippet(self, name: str, code: str, language: str = "python", description: str = "") -> Dict[str, Any]:
        with closing(self._connect()) as conn, conn:
            conn.execute("INSERT OR REPLACE INTO snippets (name, language, code, description) VALUES (?,?,?,?)", (name, language, code, description))
        return {"ok": True, "snippet": name}

    def get_snippet(self, name: str) -> Dict[str, Any]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM snippets WHERE name=?", (name,)).fetchone()
        if not row:
            return {"ok": False, "error": f"no snippet called '{name}'"}
        return {"ok": True, **dict(row)}

    def forget(self, category: str, key: Optional[str] = None) -> Dict[str, Any]:
        with closing(self._connect()) as conn, conn:
            if key:
                cur = conn.execute("DELETE FROM knowledge WHERE category=? AND key=?", (category.strip().lower(), key))
            else:
                cur = conn.execute("DELETE FROM knowledge WHERE category=?", (category.strip().lower(),))
        return {"ok": cur.rowcount > 0, "removed": cur.rowcount}

    def stats(self) -> Dict[str, Any]:
        with closing(self._connect()) as conn:
            facts = conn.execute("SELECT COUNT(*) AS n FROM knowledge").fetchone()["n"]
            snippets = conn.execute("SELECT COUNT(*) AS n FROM snippets").fetchone()["n"]
        return {"knowledge_rows": facts, "snippets": snippets, "path": str(self.path), "size_bytes": self.path.stat().st_size if self.path.exists() else 0}


def _decode(value: str) -> Any:
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


_db: Optional[KnowledgeDB] = None


def get_db() -> KnowledgeDB:
    global _db
    if _db is None:
        _db = KnowledgeDB()
    return _db
