"""Paths, environment loading and user settings for Nova."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULTS: Dict[str, Any] = {
    "engine": "auto",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2",
    "hf_model": "meta-llama/Llama-3.1-8B-Instruct:fastest",
    "hf_max_tokens": 700,
    "groq_model": "llama-3.3-70b-versatile",
    "openai_model": "gpt-4o-mini",
    "gemini_model": "gemini-2.5-flash",
    "max_steps": 12,
    "voice": "off",
    "approval_mode": "ask",
}


def _find_home(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").is_dir() or (candidate / "pyproject.toml").is_file():
            return candidate
    return start


NOVA_HOME = Path(os.environ.get("NOVA_HOME") or _find_home(Path.cwd())).resolve()
STATE_DIR = NOVA_HOME / ".nova"
WORKSPACE = Path(os.environ.get("NOVA_WORKSPACE") or NOVA_HOME / "workspace").resolve()
SETTINGS_FILE = STATE_DIR / "settings.json"
MEMORY_FILE = STATE_DIR / "memory.json"
SKILLS_FILE = STATE_DIR / "skills.json"
KNOWLEDGE_DB = STATE_DIR / "knowledge.db"
TRACES_FILE = STATE_DIR / "traces.jsonl"
LOG_FILE = STATE_DIR / "nova.log"

ENV_SETTINGS = {
    "ollama_url": "OLLAMA_URL",
    "ollama_model": "OLLAMA_MODEL",
    "hf_model": "HF_MODEL",
    "hf_max_tokens": "HF_MAX_TOKENS",
}

OVERRIDES: Dict[str, Any] = {}


def load_env() -> None:
    """Populate os.environ from .env files already present on disk."""
    seen = set()
    for path in (NOVA_HOME / ".env", NOVA_HOME / "Config" / ".env", Path.cwd() / ".env"):
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            continue


def ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_settings() -> Dict[str, Any]:
    settings = dict(DEFAULTS)
    settings.update(_read_json(SETTINGS_FILE))
    return settings


def save_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_settings()
    settings.update(patch)
    ensure_dirs()
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings


def get(key: str, default: Any = None) -> Any:
    """Flag (--engine) beats shell/.env (OLLAMA_URL) beats saved settings beats shipped default."""
    if key in OVERRIDES:
        return OVERRIDES[key]
    env_name = ENV_SETTINGS.get(key)
    from_env = os.environ.get(env_name) if env_name else None
    if from_env:
        return from_env
    return load_settings().get(key, DEFAULTS.get(key, default))


def override(key: str, value: Any) -> None:
    """Session flag (--mode, --engine) without rewriting the user's saved settings."""
    if value is not None:
        OVERRIDES[key] = value


def api_key_present(name: str) -> bool:
    return bool(os.environ.get(name))


def mask(value: Optional[str]) -> str:
    if not value:
        return ""
    return f"{value[:4]}...{value[-2:]}" if len(value) > 8 else "set"
