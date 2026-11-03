"""Host introspection tools - read-only, so the agent knows what machine it is on."""

from __future__ import annotations

import os
import platform
import sys
from typing import Any, Dict

from .. import config


def system_info(**args: Any) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "ok": True,
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "home": str(config.NOVA_HOME),
        "workspace": str(config.WORKSPACE),
    }
    try:
        import psutil
    except ImportError:
        info["psutil"] = False
        return info

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(config.NOVA_HOME))
    info.update(
        {
            "psutil": True,
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "memory_percent": mem.percent,
            "memory_total_gb": round(mem.total / 1024**3, 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / 1024**3, 2),
            "uptime_seconds": round(__import__("time").time() - psutil.boot_time()),
        }
    )
    return info


def top_processes(limit: int = 12, **args: Any) -> Dict[str, Any]:
    try:
        import psutil
    except ImportError:
        return {"ok": False, "error": "psutil is not installed - run `pip install psutil`"}
    rows = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            if proc.info.get("name"):
                rows.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rows.sort(key=lambda r: (r.get("cpu_percent") or 0), reverse=True)
    return {"ok": True, "count": len(rows), "processes": rows[: int(limit)]}


def environment(**args: Any) -> Dict[str, Any]:
    from ..engine import get_registry

    keys = {name: bool(os.environ.get(name)) for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "HF_TOKEN")}
    return {
        "ok": True,
        "api_keys": keys,
        "engines": [{"name": row["name"], "available": row["available"], "model": row["model"]} for row in get_registry().status()],
        "optional_libs": {name: _has(name) for name in ("psutil", "pyautogui", "requests", "rich", "whisper", "edge_tts", "pyttsx3")},
    }


def _has(module: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False
