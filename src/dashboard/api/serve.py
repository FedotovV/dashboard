"""Локальная раздача экранов. Слепок только читается. Правки пишутся в свой файл."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dashboard.api.page import render_sprint
from dashboard.api.period import render_period
from dashboard.api.read import RouteError, load_snapshot, metric_brief, resolve_snapshot, sprint_view, team_view
from dashboard.edits.store import EditsError, empty_document, merge_form, read_document, read_edits, store_document


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
    edits_path: Path | None = None,
) -> ThreadingHTTPServer:
    require_localhost(host)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/edits":
                self._edits_get()
                return
            day = (parse_qs(parsed.query).get("date") or [default_day])[0]
            try:
                path = resolve_snapshot(snapshots, team_id, day)
                document = load_snapshot(path)
                if parsed.path == "/":
                    body = render_sprint(sprint_view(document)).encode("utf-8")
                    self._send(200, "text/html; charset=utf-8", body)
                    return
                if parsed.path == "/period":
                    view = team_view(document, read_edits(edits_path))
                    view["editsEnabled"] = edits_path is not None
                    body = render_period(view).encode("utf-8")
                    self._send(200, "text/html; charset=utf-8", body)
                    return
                if parsed.path == "/api/sprint":
                    self._send(200, "application/json; charset=utf-8", _json(sprint_view(document)))
                    return
                if parsed.path == "/api/team":
                    view = team_view(document, read_edits(edits_path))
                    view["editsEnabled"] = edits_path is not None
                    self._send(200, "application/json; charset=utf-8", _json(view))
                    return
                prefix = "/api/metrics/"
                if parsed.path.startswith(prefix):
                    metric_id = parsed.path[len(prefix):]
                    self._send(200, "application/json; charset=utf-8", _json(metric_brief(document, metric_id)))
                    return
                self._send(404, "text/plain; charset=utf-8", "нет такого пути".encode())
            except RouteError as exc:
                self._send(exc.status, "application/json; charset=utf-8", _json({"error": exc.message}))
            except EditsError as exc:
                self._send(exc.status, "application/json; charset=utf-8", _json({"error": exc.message}))

        def do_PUT(self) -> None:  # noqa: N802
            self._write_edits(form=False)

        def do_POST(self) -> None:  # noqa: N802
            kind = self.headers.get("Content-Type") or ""
            self._write_edits(form="application/json" not in kind)

        def log_message(self, fmt: str, *args) -> None:
            return

        def _edits_get(self) -> None:
            if edits_path is None:
                self._send(404, "application/json; charset=utf-8", _json({"error": "файл правок не подключён"}))
                return
            try:
                document = read_document(edits_path) or empty_document(team_id)
            except EditsError as exc:
                self._send(exc.status, "application/json; charset=utf-8", _json({"error": exc.message}))
                return
            self._send(200, "application/json; charset=utf-8", _json(document))

        def _write_edits(self, form: bool) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/edits":
                self._send(405, "text/plain; charset=utf-8", "запись с экрана не принимается".encode())
                return
            if edits_path is None:
                self._send(404, "application/json; charset=utf-8", _json({"error": "файл правок не подключён"}))
                return
            try:
                raw = self._read_body()
                if form:
                    fields = {
                        key: values[-1]
                        for key, values in parse_qs(raw.decode("utf-8"), keep_blank_values=True).items()
                    }
                    document = merge_form(edits_path, team_id, fields, datetime.now(timezone.utc))
                    self.send_response(303)
                    self.send_header("Location", "/period")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                document = store_document(edits_path, json.loads(raw.decode("utf-8")), team_id)
            except (EditsError, json.JSONDecodeError, UnicodeError) as exc:
                message = exc.message if isinstance(exc, EditsError) else "тело не читается"
                status = exc.status if isinstance(exc, EditsError) else 422
                self._send(status, "application/json; charset=utf-8", _json({"error": message}))
                return
            self._send(200, "application/json; charset=utf-8", _json(document))

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > 1_000_000:
                raise EditsError(413, "тело слишком большое")
            return self.rfile.read(length)

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), Handler)


def _json(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
