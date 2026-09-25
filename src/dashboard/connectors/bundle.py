"""fixture читает уже канонический JSON. file и live собирают один и тот же bundle из тел Jira."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class CollectError(ValueError):
    """Сырьё нельзя собрать в bundle."""


def collect_bundle(
    mode: str,
    source: Path,
    sources: dict,
    *,
    transport=None,
    now: datetime | None = None,
    environ: dict | None = None,
) -> dict:
    if mode == "live":
        from dashboard.connectors.jira import fetch_server

        return fetch_server(sources, transport=transport, now=now, environ=environ)
    if mode == "fixture":
        return _fixture(source)
    if mode == "file":
        return _file(source, sources)
    raise CollectError(f"неизвестный режим sources.mode: {mode}")


def _fixture(source: Path) -> dict:
    if not source.is_file():
        raise CollectError("для режима fixture нужен файл canonical JSON")
    try:
        data = json.loads(source.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectError("файл фикстуры не читается") from exc
    if not isinstance(data, dict):
        raise CollectError("фикстура должна быть объектом")
    return data


def _file(source: Path, sources: dict) -> dict:
    if not source.is_dir():
        raise CollectError("для режима file нужен каталог выгрузки")
    return bundle_from_bodies(
        _read_json(source / "meta.json"),
        _read_json(source / "search.json"),
        _read_json(source / "changelogs.json"),
        _read_json(source / "sprints.json"),
        sources,
    )


def bundle_from_bodies(meta: dict, search: dict, changelogs: dict, sprints_raw, sources: dict) -> dict:
    """Один разбор для файла и для записанного ответа API."""
    jira = sources.get("jira") or {}
    deployment = jira.get("deployment")
    if deployment not in ("cloud", "server"):
        raise CollectError("sources.jira.deployment должен быть cloud или server")
    if not isinstance(meta, dict) or not meta.get("bundleId") or not meta.get("asOf"):
        raise CollectError("meta.json должен содержать bundleId и asOf")
    if not isinstance(search, dict) or not isinstance(search.get("issues"), list):
        raise CollectError("search.json должен содержать массив issues")
    if not isinstance(changelogs, dict):
        raise CollectError("changelogs.json должен быть объектом по id задачи")
    sprints = _sprints(sprints_raw)
    field_id = ((jira.get("fields") or {}).get("storyPoints")) or None
    epic_field = ((jira.get("fields") or {}).get("epicLink")) or None
    issues = [
        _issue(raw, deployment, field_id, epic_field, _history_of(changelogs, raw.get("id")))
        for raw in search["issues"]
    ]
    _resolve_parents(issues)
    links = _links(search["issues"])
    status_changes = _status_changes(issues)
    memberships = _memberships(issues, sprints)
    issues.sort(key=lambda item: item["id"])
    return {
        "bundleId": str(meta["bundleId"]),
        "asOf": _instant(str(meta["asOf"])),
        "sourceWatermark": str(meta.get("sourceWatermark") or "file"),
        "issues": issues,
        "statusChanges": status_changes,
        "memberships": memberships,
        "sprints": sprints,
        "links": links,
    }


def _read_json(path: Path):
    if not path.is_file():
        raise CollectError(f"в выгрузке нет {path.name}")
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectError(f"{path.name} не читается") from exc


def _history_of(changelogs: dict, issue_id) -> list[dict]:
    entry = changelogs.get(str(issue_id))
    if entry is None:
        return []
    if not isinstance(entry, dict):
        raise CollectError(f"журнал {issue_id} должен быть объектом")
    histories = entry.get("histories")
    if histories is None and isinstance(entry.get("changelog"), dict):
        histories = entry["changelog"].get("histories")
    if not isinstance(histories, list):
        raise CollectError(f"у {issue_id} нет histories")
    return histories


def _issue(raw: dict, deployment: str, field_id: str | None, epic_field: str | None, histories: list[dict]) -> dict:
    if not isinstance(raw, dict) or "fields" not in raw:
        raise CollectError("у задачи нет fields")
    fields = raw["fields"] or {}
    if not isinstance(fields, dict):
        raise CollectError("fields задачи должны быть объектом")
    issue_type = fields.get("issuetype") or {}
    project = fields.get("project") or {}
    status = (fields.get("status") or {}).get("name")
    if not raw.get("id") or not raw.get("key") or not issue_type.get("name") or not project.get("key") or not status:
        raise CollectError("у задачи нет id, key, типа, проекта или статуса")
    if not fields.get("created"):
        raise CollectError(f"{raw.get('key')}: нет created")
    created = _instant(str(fields["created"]))
    points = _points(fields.get(field_id)) if field_id else None
    return {
        "id": str(raw["id"]),
        "key": str(raw["key"]),
        "summary": fields.get("summary") or "",
        "type": str(issue_type["name"]),
        "projectKey": str(project["key"]),
        "status": str(status),
        "assigneeAccountId": _assignee(fields.get("assignee"), deployment),
        "priority": _priority(fields.get("priority")),
        "storyPoints": points,
        "storyPointsAtAdd": points,
        "dueDate": _due(fields.get("duedate")),
        "resolutionAt": _instant(str(fields["resolutiondate"])) if fields.get("resolutiondate") else None,
        "created": created,
        "labels": [str(label) for label in (fields.get("labels") or [])],
        "parentId": _parent_raw(fields, epic_field),
        "subtask": bool(issue_type.get("subtask")),
        "_intervals": _intervals(histories, created, status),
        "_memberships": list(_items(histories, "Sprint")),
        "_pointChanges": _point_changes(histories, field_id),
    }


def _resolve_parents(issues: list[dict]) -> None:
    by_id = {issue["id"] for issue in issues}
    by_key = {issue["key"]: issue["id"] for issue in issues}
    for issue in issues:
        parent = issue["parentId"]
        if parent is None:
            continue
        if parent in by_id:
            continue
        if parent in by_key:
            issue["parentId"] = by_key[parent]


def _parent_raw(fields: dict, epic_field: str | None):
    parent = fields.get("parent")
    if isinstance(parent, dict) and parent.get("id"):
        return str(parent["id"])
    if not epic_field:
        return None
    epic = fields.get(epic_field)
    if epic is None or epic == "":
        return None
    if isinstance(epic, dict):
        if epic.get("id"):
            return str(epic["id"])
        if epic.get("key"):
            return str(epic["key"])
        return None
    return str(epic)


def _assignee(assignee, deployment: str) -> str | None:
    if not isinstance(assignee, dict):
        return None
    if deployment == "cloud":
        value = assignee.get("accountId")
    else:
        value = assignee.get("name") or assignee.get("key")
    if value is None or value == "":
        return None
    return str(value)


def _priority(priority) -> str | None:
    if not isinstance(priority, dict) or not priority.get("name"):
        return None
    return str(priority["name"])


def _intervals(histories: list[dict], created: str, current: str) -> list[dict]:
    events: list[tuple[str, str, str]] = []
    for created_at, item in _items(histories, "status"):
        events.append((created_at, str(item.get("fromString") or ""), str(item.get("toString") or "")))
    opened: list[tuple[str, str]] = []
    if not events:
        opened.append((created, current))
    else:
        if events[0][1]:
            opened.append((created, events[0][1]))
        for entered, _origin, target in events:
            if not target:
                raise CollectError("в журнале пустой новый статус")
            opened.append((entered, target))
    if opened[-1][1] != current:
        raise CollectError(f"последний статус журнала {opened[-1][1]} не равен текущему {current}")
    rows = []
    for index, (entered, status) in enumerate(opened):
        exited = opened[index + 1][0] if index + 1 < len(opened) else None
        rows.append({"status": status, "enteredAt": entered, "exitedAt": exited})
    return rows


def _memberships(issues: list[dict], sprints: list[dict]) -> list[dict]:
    by_id = {sprint["id"]: sprint["id"] for sprint in sprints}
    by_name = {sprint["name"]: sprint["id"] for sprint in sprints}
    rows = []
    for issue in issues:
        open_at: dict[str, str] = {}
        closed: list[tuple[str, str, str | None]] = []
        for created_at, item in issue.pop("_memberships"):
            before = _sprint_ids(item.get("from"), item.get("fromString"), by_id, by_name)
            after = _sprint_ids(item.get("to"), item.get("toString"), by_id, by_name)
            for sprint_id in sorted(after - before):
                open_at.setdefault(sprint_id, created_at)
            for sprint_id in sorted(before - after):
                added = open_at.pop(sprint_id, None)
                if added is not None:
                    closed.append((sprint_id, added, created_at))
        for sprint_id, added in open_at.items():
            closed.append((sprint_id, added, None))
        added_times = [added for _sprint, added, _removed in closed]
        issue["storyPointsAtAdd"] = _points_at(issue.pop("_pointChanges", []), issue["storyPoints"], min(added_times) if added_times else None)
        for sprint_id, added, removed in closed:
            rows.append(
                {
                    "issueId": issue["id"],
                    "sprintId": sprint_id,
                    "addedAt": added,
                    "removedAt": removed,
                }
            )
    rows.sort(key=lambda item: (item["issueId"], item["sprintId"], item["addedAt"]))
    return rows


def _status_changes(issues: list[dict]) -> list[dict]:
    rows = []
    for issue in issues:
        for interval in issue.pop("_intervals"):
            rows.append({"issueId": issue["id"], **interval})
    rows.sort(key=lambda item: (item["issueId"], item["enteredAt"], item["status"]))
    return rows


def _sprint_ids(id_field, string_field, by_id: dict[str, str], by_name: dict[str, str]) -> set[str]:
    found = _match_tokens(id_field, by_id, by_name)
    if _tokens(id_field):
        return found
    return _match_tokens(string_field, by_id, by_name)


def _match_tokens(value, by_id: dict[str, str], by_name: dict[str, str]) -> set[str]:
    found = set()
    for token in _tokens(value):
        if token in by_id:
            found.add(by_id[token])
        elif token in by_name:
            found.add(by_name[token])
    return found


def _tokens(value) -> list[str]:
    if value is None:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _items(histories: list[dict], field: str | None = None):
    stamped = []
    for index, history in enumerate(histories):
        if not isinstance(history, dict) or not history.get("created"):
            raise CollectError("у записи журнала нет created")
        stamped.append((_instant(str(history["created"])), index, history))
    stamped.sort(key=lambda item: (item[0], item[1]))
    for created_at, _index, history in stamped:
        for item in history.get("items") or []:
            if isinstance(item, dict) and (field is None or item.get("field") == field):
                yield created_at, item


def _point_changes(histories: list[dict], field_id: str | None) -> list[tuple[str, object, object]]:
    if not field_id:
        return []
    changes = []
    for created_at, item in _items(histories):
        if item.get("fieldId") == field_id:
            changes.append((created_at, _points(item.get("fromString")), _points(item.get("toString"))))
    return changes


def _points_at(changes: list[tuple[str, object, object]], current, moment: str | None):
    if not changes or moment is None:
        return current
    earlier = [change for change in changes if change[0] <= moment]
    if earlier:
        return earlier[-1][2]
    return changes[0][1]


def _points(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise CollectError("оценка не число")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CollectError("оценка не число") from exc
    if number.is_integer():
        return int(number)
    return number


def _due(value) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    day = text.split("T", 1)[0]
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError as exc:
        raise CollectError("duedate не дата") from exc
    return day


def _sprints(raw) -> list[dict]:
    values = raw.get("values") if isinstance(raw, dict) else raw
    if not isinstance(values, list) or not values:
        raise CollectError("sprints.json должен содержать спринты")
    rows = []
    for item in values:
        if not isinstance(item, dict) or item.get("id") is None:
            raise CollectError("у спринта нет id")
        state = item.get("state")
        if state not in ("future", "active", "closed"):
            raise CollectError(f"неизвестный state спринта {item.get('id')}")
        if not item.get("startDate") or not item.get("endDate"):
            raise CollectError(f"у спринта {item.get('id')} нет дат")
        rows.append(
            {
                "id": str(item["id"]),
                "name": str(item.get("name") or item["id"]),
                "state": state,
                "start": _sprint_day(str(item["startDate"])),
                "end": _sprint_day(str(item["endDate"])),
            }
        )
    rows.sort(key=lambda item: item["id"])
    return rows


def _links(issues: list[dict]) -> list[dict]:
    found = set()
    for raw in issues:
        if not isinstance(raw, dict):
            continue
        fields = raw.get("fields") or {}
        owner = str(raw.get("id"))
        for link in fields.get("issuelinks") or []:
            if not isinstance(link, dict):
                continue
            kind = ((link.get("type") or {}).get("name")) or ""
            if not kind:
                raise CollectError("у связи нет типа")
            outward = link.get("outwardIssue")
            inward = link.get("inwardIssue")
            if isinstance(outward, dict) and outward.get("id"):
                found.add((owner, str(outward["id"]), str(kind)))
            if isinstance(inward, dict) and inward.get("id"):
                found.add((str(inward["id"]), owner, str(kind)))
    rows = [{"fromId": source, "toId": target, "type": kind} for source, target, kind in sorted(found)]
    return rows


def _sprint_day(value: str) -> str:
    if "T" not in value:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise CollectError("дата спринта не читается") from exc
        return value
    instant = _aware(value)
    return instant.astimezone(instant.tzinfo).date().isoformat()


def _instant(value: str) -> str:
    return _aware(value).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _aware(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if len(text) >= 5 and text[-5] in "+-" and text[-3] != ":":
        text = text[:-2] + ":" + text[-2:]
    try:
        instant = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CollectError(f"время не читается: {value}") from exc
    if instant.tzinfo is None:
        raise CollectError(f"время без зоны: {value}")
    return instant
