"""Workspace-sandboxed filesystem tools."""

from __future__ import annotations

import fnmatch
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .. import config

TEXT_LIMIT = 60_000
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".nova"}


class SandboxError(ValueError):
    pass


def root() -> Path:
    config.ensure_dirs()
    return Path(config.WORKSPACE).resolve()


def _dedupe_root(candidate: Path, base: Path) -> Path:
    """`workspace/x.md` is how the sandbox looks from the project root; relative to the sandbox it is `x.md`.

    Only used when the literal path is missing, so a real file named workspace/ inside the workspace wins.
    """
    if candidate.exists() or not candidate.is_relative_to(base):
        return candidate
    parts = candidate.relative_to(base).parts
    if len(parts) > 1 and parts[0] == base.name:
        alias = base.joinpath(*parts[1:])
        if alias.exists():
            return alias
    return candidate


def resolve(path: str | None) -> Dict[str, Any]:
    """Resolve a request against the workspace and report whether it escaped."""
    base = root()
    raw = (path or ".").strip() or "."
    candidate = Path(os.path.expanduser(raw))
    if not candidate.is_absolute():
        candidate = _dedupe_root(base / candidate, base)
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise SandboxError(f"cannot resolve '{path}': {exc}") from exc
    inside = resolved == base or str(resolved).lower().startswith(str(base).lower() + os.sep)
    return {"path": resolved, "inside": inside, "exists": resolved.exists(), "rel": str(resolved)[len(str(base)) :].lstrip(os.sep) or "."}


def _guard(located: Dict[str, Any], args: Dict[str, Any]) -> None:
    """Escape check happens before any existence probe, so the sandbox never leaks paths."""
    if not located["inside"] and not args.get("allow_outside"):
        raise SandboxError(
            f"'{located['path']}' is outside the workspace ({root()}). "
            "Pass allow_outside=true and approve the prompt to act there."
        )


def require_exists(located: Dict[str, Any]) -> None:
    if not located["exists"]:
        raise SandboxError(
            f"not found: {located['path']} - relative paths start at the workspace root ({root()}), "
            "so pass the name from there and use list_dir to see what exists"
        )


def list_dir(path: str = ".", recursive: bool = False, limit: int = 300, **args: Any) -> Dict[str, Any]:
    located = resolve(path)
    _guard(located, args)
    require_exists(located)
    base = located["path"]
    entries: List[Dict[str, Any]] = []
    if base.is_file():
        stat = base.stat()
        entries.append({"name": base.name, "kind": "file", "size": stat.st_size})
    elif recursive:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                full = Path(dirpath) / name
                entries.append({"name": str(full.relative_to(base)), "kind": "file", "size": full.stat().st_size})
                if len(entries) >= limit:
                    break
            if len(entries) >= limit:
                break
    else:
        for child in sorted(base.iterdir(), key=lambda c: (c.is_file(), c.name.lower())):
            entries.append({"name": child.name, "kind": "dir" if child.is_dir() else "file", "size": child.stat().st_size})
    return {"ok": True, "root": str(base), "count": len(entries), "entries": entries, "truncated": len(entries) >= limit}


def read_file(path: str, max_bytes: int = TEXT_LIMIT, **args: Any) -> Dict[str, Any]:
    located = resolve(path)
    _guard(located, args)
    require_exists(located)
    target = located["path"]
    if not target.is_file():
        return {"ok": False, "error": f"not a regular file: {target}"}
    size = target.stat().st_size
    data = target.read_bytes()[: int(max_bytes)]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
        return {"ok": True, "path": str(target), "binary": True, "size": size, "preview_hex": data[:64].hex()}
    return {"ok": True, "path": str(target), "size": size, "lines": text.count("\n") + 1, "truncated": size > len(data), "content": text}


def write_file(path: str, content: str, append: bool = False, **args: Any) -> Dict[str, Any]:
    located = resolve(path)
    _guard(located, args)
    target = located["path"]
    if target.is_dir():
        return {"ok": False, "error": f"path is a directory: {target}"}
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(target, mode, encoding="utf-8", newline=os.linesep) as handle:
        handle.write(content)
    return {"ok": True, "path": str(target), "bytes": len(content.encode('utf-8')), "appended": bool(append)}


def make_dir(path: str, **args: Any) -> Dict[str, Any]:
    located = resolve(path)
    _guard(located, args)
    located["path"].mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": str(located["path"])}


def move_path(src: str, dst: str, **args: Any) -> Dict[str, Any]:
    a, b = resolve(src), resolve(dst)
    _guard(a, args)
    _guard(b, args)
    require_exists(a)
    if b["path"].exists():
        return {"ok": False, "error": f"destination already exists: {b['path']}"}
    b["path"].parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(a["path"]), str(b["path"]))
    return {"ok": True, "from": str(a["path"]), "to": str(b["path"])}


def delete_path(path: str, **args: Any) -> Dict[str, Any]:
    located = resolve(path)
    _guard(located, args)
    require_exists(located)
    target = located["path"]
    if target == root():
        return {"ok": False, "error": "refusing to delete the workspace root"}
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "deleted": str(target)}


def find_files(pattern: str = "*", path: str = ".", limit: int = 200, **args: Any) -> Dict[str, Any]:
    located = resolve(path)
    _guard(located, args)
    require_exists(located)
    base = located["path"]
    matches: List[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if fnmatch.fnmatch(name.lower(), pattern.lower()):
                matches.append(str((Path(dirpath) / name).relative_to(base)))
                if len(matches) >= limit:
                    return {"ok": True, "pattern": pattern, "matches": matches, "truncated": True}
    return {"ok": True, "pattern": pattern, "count": len(matches), "matches": matches, "truncated": False}


def search_content(query: str, path: str = ".", max_files: int = 400, **args: Any) -> Dict[str, Any]:
    located = resolve(path)
    _guard(located, args)
    require_exists(located)
    base = located["path"]
    hits: List[Dict[str, Any]] = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if scanned >= max_files:
                break
            scanned += 1
            full = Path(dirpath) / name
            try:
                if full.stat().st_size > 2_000_000:
                    continue
                text = full.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if query.lower() in line.lower():
                    hits.append({"file": str(full.relative_to(base)), "line": number, "text": line.strip()[:200]})
                    if len(hits) >= 60:
                        return {"ok": True, "query": query, "hits": hits, "truncated": True}
            if len(hits) >= 60:
                break
        if len(hits) >= 60 or scanned >= max_files:
            break
    return {"ok": True, "query": query, "count": len(hits), "scanned": scanned, "hits": hits, "truncated": False}


def workspace_info(**args: Any) -> Dict[str, Any]:
    base = root()
    files = 0
    size = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            files += 1
            try:
                size += (Path(dirpath) / name).stat().st_size
            except OSError:
                pass
    return {"ok": True, "workspace": str(base), "files": files, "bytes": size, "home": str(config.NOVA_HOME)}
