"""Permission gate: the agent cannot touch the machine without a decision here."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

READ = "read"
WRITE = "write"
EXEC = "exec"
DESTRUCTIVE = "destructive"

RISK_ORDER = {READ: 0, WRITE: 1, EXEC: 2, DESTRUCTIVE: 3}

HARD_BLOCKS: Tuple[Tuple[str, str], ...] = (
    (r"rm\s+-rf\s+(/|c:\\?|\\)?\s*$", "recursive delete of a filesystem root"),
    (r"mkfs(\.|\s)", "filesystem format"),
    (r"format\s+[a-z]:\s*/q", "drive format"),
    (r":\(\)\s*\{.*\};.*:", "fork bomb"),
    (r"\bdel\s+(?:/[a-z]+\s+)+[a-z]:\\?\s*$", "recursive delete of a drive root"),
    (r"\bshutdown\b.*/[ft]", "system shutdown"),
    (r"curl[^|]*\|\s*(ba)?sh", "piping a remote script straight into a shell"),
)


@dataclass
class Decision:
    allowed: bool
    reason: str
    remembered: bool = False


@dataclass
class PermissionGate:
    """mode: ask = prompt per risky call, yolo = approve everything except hard blocks, deny = block all writes."""

    mode: str = "ask"
    auto_risk: str = READ
    session_allowed: Dict[str, str] = field(default_factory=dict)
    prompts: int = 0
    denials: int = 0
    interactive: bool = field(default_factory=lambda: sys.stdin.isatty())

    def hard_block_reason(self, text: str) -> Optional[str]:
        low = (text or "").lower()
        for pattern, label in HARD_BLOCKS:
            if re.search(pattern, low):
                return label
        return None

    def needs_approval(self, risk: str, tool_name: str) -> bool:
        if RISK_ORDER.get(risk, EXEC) <= RISK_ORDER.get(self.auto_risk, READ):
            return False
        if self.mode == "yolo":
            return False
        if tool_name in self.session_allowed:
            return False
        return True

    def review(self, tool_name: str, risk: str, args: Dict, summary: str) -> Decision:
        blocked = self.hard_block_reason(summary)
        if blocked:
            self.denials += 1
            return Decision(False, f"hard-blocked: {blocked}")

        if tool_name in self.session_allowed and RISK_ORDER.get(risk, EXEC) > RISK_ORDER.get(self.auto_risk, READ):
            return Decision(True, "approved earlier this session")

        if not self.needs_approval(risk, tool_name):
            return Decision(True, "auto-approved")

        if self.mode == "deny":
            self.denials += 1
            return Decision(False, f"mode 'deny' blocks {risk} actions ({tool_name})")

        if not self.interactive:
            self.denials += 1
            return Decision(False, self._no_tty_reason(risk))

        return self._prompt(tool_name, risk, summary)

    def _no_tty_reason(self, risk: str) -> str:
        return f"stdin is not a TTY, so approval cannot be collected - re-run with --yolo to allow {risk} actions"

    def _prompt(self, tool_name: str, risk: str, summary: str) -> Decision:
        self.prompts += 1
        print(f"\n  [{risk.upper()}] {tool_name} wants to:")
        print(f"      {summary[:400]}")
        try:
            answer = input("  allow? [y] once / [a] always this session / [n] deny > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            self.interactive = False
            self.denials += 1
            return Decision(False, self._no_tty_reason(risk))

        if answer in ("y", "yes"):
            return Decision(True, "approved once")
        if answer in ("a", "always"):
            self.session_allowed[tool_name] = risk
            return Decision(True, "approved for session", remembered=True)
        self.denials += 1
        return Decision(False, "denied by user")

    def summarize(self, tool_name: str, args: Dict) -> str:
        if tool_name == "run_command":
            return str(args.get("command", ""))
        if tool_name == "run_python":
            return f"python - <<code {len(str(args.get('code', '')))} chars>"
        path = args.get("path") or args.get("src") or args.get("pattern") or ""
        extra = args.get("content") or args.get("dst") or args.get("query") or ""
        return f"{path} {str(extra)[:80] if extra else ''}".strip()

    def stats(self) -> Dict[str, int]:
        return {"prompts": self.prompts, "denials": self.denials, "session_grants": len(self.session_allowed)}


def default_mode(cli_mode: Optional[str] = None) -> str:
    if cli_mode:
        return cli_mode
    if os.environ.get("NOVA_YOLO") == "1":
        return "yolo"
    from . import config

    return str(config.get("approval_mode", "ask"))
