"""Nova over HTTP: two endpoints and one deliberately handicapped agent.

Stdlib `http.server` rather than Flask or FastAPI, so `nova serve` adds no
dependency and a deploy image is `pip install .` on a slim Python base.

The agent behind POST /agent is weaker than the one behind `nova go` on purpose:
its gate is pinned to deny anything above `read` and its registry drops the
`allow_outside` escape hatch. A network caller gets the workspace, not the host.
"""

from __future__ import annotations

import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

from . import __version__, config
from .agents import ReactAgent
from .engine import get_registry as engine_registry
from .security import READ, PermissionGate
from .tools import Registry, build_registry

MAX_BODY_BYTES = 64 * 1024
MAX_GOAL_CHARS = 4000
MAX_STEPS = 24
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


class ServerConfigError(RuntimeError):
    """The server refuses to start rather than come up open."""


def api_token() -> str:
    return (os.environ.get("NOVA_API_TOKEN") or "").strip()


def resolve_bind(host: Optional[str], port: Optional[int]) -> Tuple[str, int]:
    """Render injects PORT, so an unset --port follows it. An unset --host stays on loopback."""
    return host or "127.0.0.1", int(port or os.environ.get("PORT") or 8000)


def read_only_gate() -> PermissionGate:
    """No approval can be collected over HTTP, so nothing above `read` is ever performed."""
    return PermissionGate(mode="deny", auto_risk=READ, interactive=False)


class ServedRegistry(Registry):
    """A tool registry for remote callers: the workspace wall has no door.

    `allow_outside` is not a declared param on any tool - handlers take it through
    `**args`, and the system prompt tells the model about it - so it is dropped here
    rather than hidden in the signature.
    """

    def call_gated(self, name: str, args: Dict[str, Any], gate: PermissionGate) -> Tuple[Dict[str, Any], str]:
        args = {key: value for key, value in (args or {}).items() if key != "allow_outside"}
        return super().call_gated(name, args, gate)


def served_registry() -> ServedRegistry:
    reg = ServedRegistry()
    reg.tools = build_registry().tools
    return reg


def health(token: str) -> Dict[str, Any]:
    """Reports configuration, not engine liveness - a slow model must not fail a platform health check."""
    active = engine_registry().active
    return {
        "ok": True,
        "service": "nova",
        "version": __version__,
        "engine": active.name if active else "not selected yet",
        "model": active.model if active else "",
        "engines": engine_registry().names(),
        "auth": "bearer token required" if token else "NOVA_API_TOKEN unset",
        "read_only": True,
    }


def agent_request(payload: Dict[str, Any]) -> Tuple[str, int, Optional[str]]:
    goal = payload.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        return "", 0, '"goal" must be a non-empty string'
    if len(goal) > MAX_GOAL_CHARS:
        return "", 0, f'"goal" is longer than {MAX_GOAL_CHARS} characters'
    raw_steps = payload.get("max_steps", config.get("max_steps", 12))
    try:
        steps = int(raw_steps)
    except (TypeError, ValueError):
        return "", 0, '"max_steps" must be an integer'
    if not 1 <= steps <= MAX_STEPS:
        return "", 0, f'"max_steps" must be between 1 and {MAX_STEPS}'
    return goal.strip(), steps, None


def authorized(header: Optional[str], token: str) -> bool:
    if not token:
        return True
    scheme, _, supplied = (header or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied.strip():
        return False
    return hmac.compare_digest(supplied.strip(), token)


class NovaHTTPRequestHandler(BaseHTTPRequestHandler):
    server: "NovaServer"

    def _send(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None, "Content-Length must be a number", 400
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            return None, f"body larger than {MAX_BODY_BYTES} bytes", 413
        try:
            raw = self.rfile.read(length) if length else b""
        except OSError:
            return None, "request body could not be read", 400
        if not raw:
            return None, 'send a JSON body, e.g. {"goal": "list the files in the workspace"}', 400
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            return None, f"body is not JSON: {exc}", 400
        if not isinstance(payload, dict):
            return None, "body must be a JSON object", 400
        return payload, None, 200

    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/health":
            self._send(200, health(self.server.token))
            return
        self._send(404, {"ok": False, "error": "unknown path - GET /health or POST /agent"})

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/agent":
            self._read_body()
            self._send(404, {"ok": False, "error": "unknown path - GET /health or POST /agent"})
            return
        if not authorized(self.headers.get("Authorization"), self.server.token):
            self._read_body()
            self._send(401, {"ok": False, "error": "missing or wrong credentials - send `Authorization: Bearer <NOVA_API_TOKEN>`"})
            return

        payload, error, status = self._read_body()
        if error:
            self._send(status, {"ok": False, "error": error})
            return
        goal, max_steps, invalid = agent_request(payload or {})
        if invalid:
            self._send(400, {"ok": False, "error": invalid})
            return

        started = time.time()
        agent = ReactAgent(gate=read_only_gate(), tools=served_registry(), max_steps=max_steps, verbose=False)
        outcome = agent.run(goal)
        self._send(200, {**outcome.as_dict(), "goal": goal, "ms": round((time.time() - started) * 1000, 1)})


class NovaServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    token = ""


def build_server(host: str = "127.0.0.1", port: int = 0, token: Optional[str] = None) -> NovaServer:
    token = api_token() if token is None else token.strip()
    if not token and host not in LOCAL_HOSTS:
        raise ServerConfigError(
            f"refusing to serve on {host} without NOVA_API_TOKEN - set the token, or bind 127.0.0.1 for local use"
        )
    server = NovaServer((host, port), NovaHTTPRequestHandler)
    server.token = token
    return server


def serve(host: Optional[str] = None, port: Optional[int] = None, token: Optional[str] = None) -> int:
    config.load_env()
    config.ensure_dirs()
    bound_host, bound_port = resolve_bind(host, port)
    try:
        server = build_server(bound_host, bound_port, token)
    except OSError as exc:
        print(f"  cannot bind {bound_host}:{bound_port} - {exc}")
        return 2

    address, port_actual = server.server_address[0], server.server_port
    print(f"  nova {__version__} | http://{address}:{port_actual} | POST /agent, GET /health")
    print(f"  actions above `read` are denied and paths stay inside {config.WORKSPACE}")
    if server.token:
        print("  every /agent call needs `Authorization: Bearer <NOVA_API_TOKEN>`")
    else:
        print("  NOVA_API_TOKEN unset - loopback only, every request on this machine is trusted")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        server.server_close()
    return 0
