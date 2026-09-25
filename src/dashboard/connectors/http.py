"""Единственное место коннектора, которое открывает сокет. Редиректы не следует."""

from __future__ import annotations

import http.client
from dataclasses import dataclass
from urllib.parse import quote, urljoin, urlsplit


class HttpError(Exception):
    """Адрес нельзя запросить."""


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes
    headers: dict[str, str]


def origin(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise HttpError("адрес Jira должен быть http или https")
    host = parts.hostname.lower()
    if parts.port is None:
        return f"{parts.scheme}://{host}"
    return f"{parts.scheme}://{host}:{parts.port}"


def build_url(base: str, path: str, query: dict[str, str] | None = None) -> str:
    root = origin(base)
    prefix = urlsplit(base).path.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    url = root + prefix + suffix
    if query:
        url = url + "?" + "&".join(f"{quote(key, safe='')}={quote(value, safe='')}" for key, value in query.items())
    if origin(url) != root:
        raise HttpError("запрос ушёл с хоста Jira")
    return url


def resolve(current: str, location: str) -> str:
    return urljoin(current, location)


def urllib_transport(url: str, headers: dict[str, str]) -> HttpResult:
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    connection = _connection(parts.scheme, parts.hostname or "", parts.port)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        status = response.status
        payload = response.read()
        found = {key.lower(): value for key, value in response.getheaders()}
    except (http.client.HTTPException, OSError) as exc:
        raise HttpError("Jira не ответила") from exc
    finally:
        connection.close()
    if status != 200:
        payload = b""
    return HttpResult(status, payload, found)


def _connection(scheme: str, host: str, port: int | None) -> http.client.HTTPConnection:
    if scheme == "https":
        return http.client.HTTPSConnection(host, port or 443, timeout=30)
    return http.client.HTTPConnection(host, port or 80, timeout=30)
