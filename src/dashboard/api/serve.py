"""Локальная раздача экранов. Слепок только читается. Правки и team.yaml пишутся в свои файлы."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dashboard.api.page import render_sprint
from dashboard.api.period import render_period
from dashboard.api.read import RouteError, load_snapshot, metric_brief, resolve_snapshot, sprint_view, team_view
from dashboard.edits.store import EditsError, empty_document, merge_form, read_document, read_edits, store_document
from dashboard.setup.page import render_setup, render_setup_error
from dashboard.setup.store import SetupError, apply_form, describe, read_document as read_team
from dashboard.setup.store import write_document


class ServeError(Exception):
    pass


def require_localhost(host: str) -> None:
    if host != "127.0.0.1":
        raise ServeError("serve слушает только 127.0.0.1")


def token_from_env(name: str | None, environ: dict) -> str | None:
    if not name:
        return None
    value = environ.get(name)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def require_bind(host: str, write_token: str | None) -> str | None:
    if host == "127.0.0.1":
        return None
    if not write_token:
        raise ServeError("нелокальный адрес требует токен на запись")
    return write_token


def same_secret(presented: str, expected: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(presented.encode("utf-8")).digest(),
        hashlib.sha256(expected.encode("utf-8")).digest(),
    )


def bearer_token(header: str | None) -> str | None:
    if header is None:
        return None
    scheme, _, rest = header.strip().partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return rest.strip()


def browser_write_allowed(
    origin: str | None,
    fetch_site: str | None,
    host_header: str | None,
    bind_host: str,
) -> bool:
    """Чужой сайт не пишет team.yaml и правки. Клиент без Origin на localhost по-прежнему пишет."""
    if (fetch_site or "").strip().lower() == "cross-site":
        return False
    request_host = _split_host(host_header)
    if bind_host == "127.0.0.1" and (request_host is None or request_host[0].lower() not in {"127.0.0.1", "localhost"}):
        return False
    if origin is None or not origin.strip():
        return True
    if origin.strip().lower() == "null":
        return False
    parts = urlparse(origin.strip())
    if parts.scheme != "http" or not parts.hostname or parts.username or parts.password or request_host is None:
        return False
    origin_port = parts.port if parts.port is not None else 80
    return parts.hostname.lower() == request_host[0].lower() and origin_port == request_host[1]


def _split_host(host_header: str | None) -> tuple[str, int] | None:
    if host_header is None:
        return None
    text = host_header.strip()
    if not text:
        return None
    if text.startswith("["):
        end = text.find("]")
        if end < 0:
            return None
        hostname = text[1:end]
        rest = text[end + 1 :]
        if not rest:
            return hostname, 80
        if not rest.startswith(":"):
            return None
        return _port(hostname, rest[1:])
    if ":" not in text:
        return text, 80
    hostname, _, raw_port = text.rpartition(":")
    return _port(hostname, raw_port)


def _port(hostname: str, raw_port: str) -> tuple[str, int] | None:
    if not hostname:
        return None
    try:
        port = int(raw_port)
    except ValueError:
        return None
    if port < 1 or port > 65535:
        return None
    return hostname, port


def make_server(
    snapshots: Path,
    team_id: str,
    host: str,
    port: int,
    default_day: str | None = None,
    edits_path: Path | None = None,
    config_path: Path | None = None,
    manifest_path: Path | None = None,
    write_token: str | None = None,
) -> ThreadingHTTPServer:
    required_token = require_bind(host, write_token)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in {"/setup", "/api/setup"}:
                self._setup_get(parsed)
                return
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
                    view["writeTokenRequired"] = required_token is not None
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
            if urlparse(self.path).path == "/api/setup":
                self._setup_write(form=False)
                return
            self._write_edits(form=False)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            kind = self.headers.get("Content-Type") or ""
            form = "application/json" not in kind
            if parsed.path == "/api/setup":
                self._setup_write(form=form)
                return
            self._write_edits(form=form)

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
                form_token = None
                if form:
                    fields = {
                        key: values[-1]
                        for key, values in parse_qs(raw.decode("utf-8"), keep_blank_values=True).items()
                    }
                    form_token = fields.pop("token", None)
                if not self._gate(form, form_token):
                    return
                if form:
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

        def _setup_get(self, parsed) -> None:
            if config_path is None:
                self._send(404, "application/json; charset=utf-8", _json({"error": "мастер настройки не подключён"}))
                return
            try:
                view = describe(config_path, team_id, manifest_path)
            except SetupError as exc:
                if parsed.path == "/api/setup":
                    self._send(exc.status, "application/json; charset=utf-8", _problem(exc))
                    return
                body = render_setup_error(exc.problems).encode("utf-8")
                self._send(exc.status, "text/html; charset=utf-8", body)
                return
            if parsed.path == "/api/setup":
                view["writeTokenRequired"] = required_token is not None
                self._send(200, "application/json; charset=utf-8", _json(view))
                return
            view["saved"] = (parse_qs(parsed.query).get("saved") or [""])[0] == "1"
            view["writeTokenRequired"] = required_token is not None
            self._send(200, "text/html; charset=utf-8", render_setup(view).encode("utf-8"))

        def _setup_write(self, form: bool) -> None:
            if config_path is None:
                self._send(404, "application/json; charset=utf-8", _json({"error": "мастер настройки не подключён"}))
                return
            document = None
            try:
                raw = self._read_body()
                form_token = None
                if form:
                    fields = {
                        key: values[-1]
                        for key, values in parse_qs(raw.decode("utf-8"), keep_blank_values=True).items()
                    }
                    form_token = fields.pop("token", None)
                if not self._gate(form, form_token):
                    return
                if form:
                    document = apply_form(read_team(config_path), fields)
                else:
                    document = json.loads(raw.decode("utf-8"))
                view = write_document(config_path, document, team_id, manifest_path, os.environ)
            except SetupError as exc:
                if form and not isinstance(document, dict) and config_path is not None:
                    try:
                        document = read_team(config_path)
                    except SetupError:
                        document = None
                self._setup_failed(exc, form, document)
                return
            except (EditsError, json.JSONDecodeError, UnicodeError) as exc:
                message = exc.message if isinstance(exc, EditsError) else "тело не читается"
                status = exc.status if isinstance(exc, EditsError) else 422
                self._setup_failed(SetupError(status, [message]), form, document)
                return
            if form:
                self.send_response(303)
                self.send_header("Location", "/setup?saved=1")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._send(200, "application/json; charset=utf-8", _json(view))

        def _setup_failed(self, exc: SetupError, form: bool, document: dict | None) -> None:
            if form and isinstance(document, dict):
                body = render_setup(
                    {
                        "document": document,
                        "manifestState": "off",
                        "needsAcceptRecompute": False,
                        "problems": exc.problems,
                        "saved": False,
                        "writeTokenRequired": required_token is not None,
                    }
                ).encode("utf-8")
                self._send(exc.status, "text/html; charset=utf-8", body)
                return
            self._send(exc.status, "application/json; charset=utf-8", _problem(exc))

        def _gate(self, form: bool, form_token: str | None) -> bool:
            if not browser_write_allowed(
                self.headers.get("Origin"),
                self.headers.get("Sec-Fetch-Site"),
                self.headers.get("Host"),
                host,
            ):
                self._cross_site(form)
                return False
            if required_token is None:
                return True
            header = bearer_token(self.headers.get("Authorization"))
            if header is None:
                presented = (form_token or "").strip() if form else ""
            else:
                presented = header
            if same_secret(presented, required_token):
                return True
            self._unauthorized(form)
            return False

        def _cross_site(self, form: bool) -> None:
            if form:
                body = (
                    "<!DOCTYPE html><html lang=\"ru\"><meta charset=\"utf-8\">"
                    "<title>Запись</title><p>Запись с другого сайта не принимается.</p>"
                ).encode()
                self._send(403, "text/html; charset=utf-8", body)
                return
            self._send(
                403,
                "application/json; charset=utf-8",
                _json({"error": "запись с другого сайта не принимается"}),
            )

        def _unauthorized(self, form: bool) -> None:
            if form:
                body = (
                    "<!DOCTYPE html><html lang=\"ru\"><meta charset=\"utf-8\">"
                    "<title>Токен</title><p>Нужен токен записи.</p>"
                ).encode()
                self._send(401, "text/html; charset=utf-8", body, authenticate=True)
                return
            self._send(
                401,
                "application/json; charset=utf-8",
                _json({"error": "нужен токен записи"}),
                authenticate=True,
            )

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > 1_000_000:
                raise EditsError(413, "тело слишком большое")
            return self.rfile.read(length)

        def _send(self, status: int, content_type: str, body: bytes, authenticate: bool = False) -> None:
            self.send_response(status)
            if authenticate:
                self.send_header("WWW-Authenticate", "Bearer")
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), Handler)


def _json(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def _problem(exc: SetupError) -> bytes:
    return _json({"error": exc.message, "problems": exc.problems})
