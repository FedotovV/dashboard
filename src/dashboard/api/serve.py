"""Локальная раздача экрана «Спринт». Слепок только читается."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dashboard.api.page import render_sprint
from dashboard.api.read import RouteError, load_snapshot, metric_brief, resolve_snapshot, sprint_view


class ServeError(Exception):
    pass


def require_localhost(host: str) -> None:
    if host != "127.0.0.1":
        raise ServeError("serve слушает только 127.0.0.1")


def make_server(
    snapshots: Path,
    team_id: str,
    host: str,
    port: int,
    default_day: str | None = None,
) -> ThreadingHTTPServer:
    require_localhost(host)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            day = (parse_qs(parsed.query).get("date") or [default_day])[0]
            try:
                path = resolve_snapshot(snapshots, team_id, day)
                document = load_snapshot(path)
                if parsed.path == "/":
                    body = render_sprint(sprint_view(document)).encode("utf-8")
                    self._send(200, "text/html; charset=utf-8", body)
                    return
                if parsed.path == "/api/sprint":
                    body = _json(sprint_view(document))
                    self._send(200, "application/json; charset=utf-8", body)
                    return
                prefix = "/api/metrics/"
                if parsed.path.startswith(prefix):
                    metric_id = parsed.path[len(prefix):]
                    body = _json(metric_brief(document, metric_id))
                    self._send(200, "application/json; charset=utf-8", body)
                    return
                self._send(404, "text/plain; charset=utf-8", "нет такого пути".encode())
            except RouteError as exc:
                self._send(exc.status, "application/json; charset=utf-8", _json({"error": exc.message}))

        def do_PUT(self) -> None:  # noqa: N802
            self._send(405, "text/plain; charset=utf-8", "запись с экрана не принимается".encode())

        def do_POST(self) -> None:  # noqa: N802
            self.do_PUT()

        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), Handler)


def _json(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
