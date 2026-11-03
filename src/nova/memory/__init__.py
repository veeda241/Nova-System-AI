"""Memory primitive: durable facts (JSON) plus structured knowledge (SQLite)."""

from __future__ import annotations

from .kb import KnowledgeDB, get_db
from .store import MemoryStore, get_store

__all__ = ["MemoryStore", "KnowledgeDB", "get_store", "get_db", "context_block"]


def context_block(query: str = "", max_chars: int = 1200) -> str:
    """What the agent is told it already knows, before it starts thinking."""
    parts: list[str] = []
    store = get_store()
    facts = store.facts()
    if facts:
        lines = [f"- {k}: {str(v)[:120]}" for k, v in list(facts.items())[:12]]
        parts.append("KNOWN FACTS:\n" + "\n".join(lines))

    recent = store.tasks(3)
    if recent:
        lines = [f"- [{t['ts']}] {'ok' if t['ok'] else 'failed'} {t['goal'][:80]}" for t in recent]
        parts.append("RECENT TASKS:\n" + "\n".join(lines))

    if query:
        hits = get_db().search(query, limit=4)
        if hits.get("ok") and hits["matches"]:
            lines = [f"- {m['category']}/{m['key']}: {str(m['value'])[:150]}" for m in hits["matches"]]
            parts.append("RELATED NOTES:\n" + "\n".join(lines))

    block = "\n\n".join(parts)
    return block[:max_chars]
