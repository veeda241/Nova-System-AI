"""Terminal rendering. Falls back to plain text when rich is not installed."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Iterable, List, Optional

try:
    from rich.console import Console
    from rich.markup import escape
    from rich.table import Table

    _console: Optional[Any] = Console()
except ImportError:
    _console = None
    Table = None  # type: ignore[assignment]
    escape = lambda text: str(text)  # noqa: E731


def force_utf8() -> None:
    """Windows consoles default to cp1252; ✓ and ✗ would raise."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


BANNER = r"""
  _   _   _   ___   _
 | \ | | | \ | | \ / /
 |  \| | |  \| |  \ /
 | |\  | | |\  |  / /
 |_| \_| |_| \_| /_/   agentic os - cli only
"""


def banner(text: str = "") -> None:
    if _console:
        _console.print(BANNER, style="cyan")
    else:
        print(BANNER)
    if text:
        print(text)


def heading(title: str) -> None:
    if _console:
        _console.print(f"\n[bold]{title}[/bold]")
    else:
        print(f"\n=== {title} ===")


def line(text: str = "") -> None:
    print(text)


def ok(text: str) -> None:
    if _console:
        _console.print(f"[green]✓[/green] {escape(str(text))}")
    else:
        print(f"[ok] {text}")


def warn(text: str) -> None:
    if _console:
        _console.print(f"[yellow]![/yellow] {escape(str(text))}")
    else:
        print(f"[!] {text}")


def fail(text: str) -> None:
    if _console:
        _console.print(f"[red]✗ {escape(str(text))}[/red]")
    else:
        print(f"[error] {text}", file=sys.stderr)


def _fit(columns: List[str], cells: List[List[str]], floors: Dict[str, int], budget: int) -> List[int]:
    """Column widths that actually fit the terminal, widest first, never below the header."""
    desired = [max([len(column)] + [len(row[i]) for row in cells]) for i, column in enumerate(columns)]
    floors = [min(desired[i], max(len(column), floors.get(column, 0))) for i, column in enumerate(columns)]
    for respect_floors in (True, False):
        floor = floors if respect_floors else [len(column) for column in columns]
        while sum(desired) > budget:
            slack = [desired[i] - floor[i] for i in range(len(desired))]
            if max(slack) <= 0:
                break
            desired[slack.index(max(slack))] -= 1
    return desired


def kv(rows: Iterable[Any], columns: List[str], min_widths: Optional[Dict[str, int]] = None) -> None:
    rows = list(rows)
    if not rows:
        print("  (nothing to show)")
        return
    cells = [[_cell(row.get(column)) for column in columns] for row in rows]
    spare = max(60, (_console.width if _console else 80)) - 3 * len(columns) - 1
    widths = _fit(columns, cells, min_widths or {}, spare)
    if _console and Table is not None:
        table = Table(show_header=True, header_style="bold")
        for column, width in zip(columns, widths):
            table.add_column(column, width=width, overflow="ellipsis", no_wrap=True)
        for row in cells:
            table.add_row(*[escape(value) for value in row])
        _console.print(table)
        return
    print("  " + "  ".join(str(column).ljust(w) for column, w in zip(columns, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for row in cells:
        print("  " + "  ".join(value[:w].ljust(w) for value, w in zip(row, widths)))


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        value = json.dumps(value, default=str)
    text = str(value)
    return text if len(text) <= 90 else text[:87] + "..."


def result(payload: Dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
        return
    if not payload.get("ok", True):
        fail(str(payload.get("error", "failed")))
        return
    body = {k: v for k, v in payload.items() if k not in ("ok", "_ms", "_tool")}
    for key, value in body.items():
        if isinstance(value, (dict, list)):
            print(f"  {key}:")
            _nested(value)
        else:
            print(f"  {key}: {value}")


def _nested(value: Any, indent: int = 2) -> None:
    pad = " " * indent
    if isinstance(value, list):
        for item in value[:40]:
            if isinstance(item, (dict, list)):
                _nested(item, indent)
            else:
                print(f"{pad}- {item}")
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                print(f"{pad}{key}:")
                _nested(item, indent + 2)
            else:
                print(f"{pad}{key}: {item}")
    else:
        print(f"{pad}{value}")
