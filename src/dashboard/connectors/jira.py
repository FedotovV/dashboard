"""Живой сбор Jira Server. Тела те же, что у файловой выгрузки. Токен в bundle не кладётся."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone

from dashboard.connectors.bundle import CollectError, bundle_from_bodies
from dashboard.connectors.http import HttpError, build_url, origin, resolve, urllib_transport

_SPRINT_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_PAGE_CAP = 20
_FIELDS = (
    "summary",
    "status",
    "issuetype",
    "project",
    "assignee",
    "priority",
    "created",
    "duedate",
    "resolutiondate",
    "labels",
    "parent",
    "issuelinks",
)


def fetch_server(sources: dict, *, transport=None, now: datetime | None = None, environ: dict | None = None) -> dict:
    jira = sources.get("jira") or {}
    if jira.get("deployment") != "server":
        raise CollectError("живой сбор в этом шаге только для Jira Server")
    base = str(jira.get("baseUrl") or "").strip()
    sprint_id = str(jira.get("sprintId") or "")
    if not base:
        raise CollectError("для live нужен sources.jira.baseUrl")
    if not _SPRINT_ID.fullmatch(sprint_id):
        raise CollectError("для live нужен sprintId из букв, цифр, точки, _ или -")
    try:
        root = origin(base)
    except HttpError as exc:
        raise CollectError(str(exc)) from exc
    env_name = jira.get("authEnv")
    if not env_name:
        raise CollectError("для live нужно имя authEnv")
    token = (environ if environ is not None else os.environ).get(env_name)
    if not token:
        raise CollectError("нет токена в окружении")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    getter = transport or urllib_transport
    try:
        sprint = _get_json(getter, base, f"/rest/agile/1.0/sprint/{sprint_id}", None, headers, root)
        issues = _search(getter, base, sprint_id, _field_names(jira), headers, root)
        changelogs = {
            str(issue.get("id")): {"histories": _changelog(getter, base, str(issue.get("id")), headers, root)}
            for issue in issues
        }
    except HttpError as exc:
        raise CollectError(str(exc)) from exc
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise CollectError("часы сбора без зоны")
    search = {"issues": issues}
    sprints = [sprint]
    meta = {
        "bundleId": f"live-{sprint_id}",
        "asOf": moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sourceWatermark": "live:" + _digest({"changelogs": changelogs, "issues": issues, "sprints": sprints}),
    }
    return bundle_from_bodies(meta, search, changelogs, sprints, sources)


def _field_names(jira: dict) -> str:
    names = list(_FIELDS)
    fields = jira.get("fields") or {}
    for key in ("storyPoints", "epicLink"):
        value = fields.get(key)
        if value:
            names.append(str(value))
    return ",".join(names)


def _search(getter, base: str, sprint_id: str, fields: str, headers: dict, root: str) -> list:
    jql = f"sprint = {sprint_id}" if sprint_id.isdigit() else f'sprint = "{sprint_id}"'

    def page(start: int) -> tuple[list, int]:
        data = _get_json(
            getter,
            base,
            "/rest/api/2/search",
            {"jql": jql, "startAt": str(start), "maxResults": "50", "fields": fields},
            headers,
            root,
        )
        issues = data.get("issues") or []
        if not isinstance(issues, list):
            raise CollectError("поиск Jira не содержит issues")
        total = data.get("total", start + len(issues))
        return issues, int(total)

    return _pages(page)


def _changelog(getter, base: str, issue_id: str, headers: dict, root: str) -> list:
    if not _SPRINT_ID.fullmatch(issue_id):
        raise CollectError("id задачи нельзя подставить в адрес")

    def page(start: int) -> tuple[list, int]:
        data = _get_json(
            getter,
            base,
            f"/rest/api/2/issue/{issue_id}/changelog",
            {"startAt": str(start), "maxResults": "100"},
            headers,
            root,
        )
        histories = data.get("histories")
        if histories is None:
            histories = data.get("values") or []
        if not isinstance(histories, list):
            raise CollectError("журнал Jira не содержит histories")
        total = data.get("total", start + len(histories))
        return histories, int(total)

    return _pages(page)


def _pages(page) -> list:
    start = 0
    rows: list = []
    for _ in range(_PAGE_CAP):
        batch, total = page(start)
        rows.extend(batch)
        if not batch or len(rows) >= total:
            return rows
        start += len(batch)
    raise CollectError("выгрузка не дочитана")


def _get_json(getter, base: str, path: str, query: dict | None, headers: dict, root: str):
    url = build_url(base, path, query)
    for _ in range(3):
        if origin(url) != root:
            raise CollectError("запрос ушёл с хоста Jira")
        result = getter(url, headers)
        status = result.status
        if status in (301, 302, 303, 307, 308):
            location = (result.headers or {}).get("location")
            if not location:
                raise CollectError(f"Jira ответила {status}")
            url = resolve(url, location)
            if origin(url) != root:
                raise CollectError("редирект уводит с хоста Jira")
            continue
        if status != 200:
            raise CollectError(f"Jira ответила {status}")
        try:
            data = json.loads(result.body.decode())
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CollectError("ответ Jira не JSON") from exc
        if not isinstance(data, dict):
            raise CollectError("ответ Jira не объект")
        return data
    raise CollectError("слишком много редиректов")


def _digest(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
