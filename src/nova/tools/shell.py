"""Shell and Python execution tools, always behind the permission gate."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from . import files


def _run(argv: Any, cwd: str | None, timeout: int, shell: bool) -> Dict[str, Any]:
    workdir = str(files.resolve(cwd)["path"]) if cwd else str(files.root())
    Path(workdir).mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONWARNINGS": "ignore"}
    try:
        proc = subprocess.run(
            argv,
            shell=shell,
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out after {timeout}s (killed)", "cwd": workdir}
    except OSError as exc:
        return {"ok": False, "error": f"could not start: {exc}", "cwd": workdir}

    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "")[:20_000],
        "stderr": (proc.stderr or "")[:8_000],
        "cwd": workdir,
    }


def run_command(command: str, cwd: str | None = None, timeout: int = 60, **args: Any) -> Dict[str, Any]:
    if not command or not command.strip():
        return {"ok": False, "error": "empty command"}
    return _run(command, cwd, int(min(max(timeout, 1), 600)), shell=True)


def run_python(code: str, timeout: int = 60, **args: Any) -> Dict[str, Any]:
    if not code or not code.strip():
        return {"ok": False, "error": "empty code"}
    return _run([sys.executable, "-B", "-c", code], None, int(min(max(timeout, 1), 600)), shell=False)


def run_python_file(path: str, timeout: int = 60, **args: Any) -> Dict[str, Any]:
    located = files.resolve(path)
    files.require_exists(located)
    if not str(located["path"]).lower().endswith(".py"):
        return {"ok": False, "error": f"not a .py file: {located['path']}"}
    return _run([sys.executable, "-B", str(located["path"])], None, int(min(max(timeout, 1), 600)), shell=False)
