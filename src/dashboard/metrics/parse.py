"""Канонический bundle в объектах. Файлов модуль не открывает."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone


def parse_datetime(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        return instant.replace(tzinfo=timezone.utc)
    return instant


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


@dataclass(frozen=True)
class Issue:
    id: str
    key: str
    summary: str
    type: str
    project_key: str
    status: str
    created: datetime
    assignee_account_id: str | None = None
    priority: str | None = None
    story_points: float | None = None
    story_points_at_add: float | None = None
    due_date: date | None = None
    resolution_at: datetime | None = None
    labels: tuple[str, ...] = ()
    parent_id: str | None = None
    subtask: bool = False


@dataclass(frozen=True)
class StatusChange:
    issue_id: str
    status: str
    entered_at: datetime
    exited_at: datetime | None = None


@dataclass(frozen=True)
class Membership:
    issue_id: str
    sprint_id: str
    added_at: datetime | None
    removed_at: datetime | None = None


@dataclass(frozen=True)
class Sprint:
    id: str
    name: str
    state: str
    start: date
    end: date


@dataclass(frozen=True)
class Link:
    from_id: str
    to_id: str
    type: str


@dataclass(frozen=True)
class Bundle:
    bundle_id: str
    as_of: datetime
    source_watermark: str
    issues: tuple[Issue, ...]
    status_changes: tuple[StatusChange, ...]
    memberships: tuple[Membership, ...]
    sprints: tuple[Sprint, ...]
    links: tuple[Link, ...]


def bundle_from_dict(data: dict) -> Bundle:
    return Bundle(
        bundle_id=data["bundleId"],
        as_of=parse_datetime(data["asOf"]),
        source_watermark=data.get("sourceWatermark") or "",
        issues=tuple(_issue(item) for item in data["issues"]),
        status_changes=tuple(_change(item) for item in data["statusChanges"]),
        memberships=tuple(_membership(item) for item in data["memberships"]),
        sprints=tuple(_sprint(item) for item in data["sprints"]),
        links=tuple(
            Link(from_id=item["fromId"], to_id=item["toId"], type=item["type"])
            for item in data["links"]
        ),
    )


def _issue(raw: dict) -> Issue:
    due = raw.get("dueDate")
    resolution = raw.get("resolutionAt")
    return Issue(
        id=raw["id"],
        key=raw["key"],
        summary=raw.get("summary") or "",
        type=raw["type"],
        project_key=raw["projectKey"],
        status=raw["status"],
        created=parse_datetime(raw["created"]),
        assignee_account_id=raw.get("assigneeAccountId"),
        priority=raw.get("priority"),
        story_points=raw.get("storyPoints"),
        story_points_at_add=raw.get("storyPointsAtAdd"),
        due_date=parse_date(due) if due else None,
        resolution_at=parse_datetime(resolution) if resolution else None,
        labels=tuple(raw.get("labels") or []),
        parent_id=raw.get("parentId"),
        subtask=bool(raw.get("subtask") or False),
    )


def _change(raw: dict) -> StatusChange:
    exited = raw.get("exitedAt")
    return StatusChange(
        issue_id=raw["issueId"],
        status=raw["status"],
        entered_at=parse_datetime(raw["enteredAt"]),
        exited_at=parse_datetime(exited) if exited else None,
    )


def _membership(raw: dict) -> Membership:
    added = raw.get("addedAt")
    removed = raw.get("removedAt")
    return Membership(
        issue_id=raw["issueId"],
        sprint_id=raw["sprintId"],
        added_at=parse_datetime(added) if added else None,
        removed_at=parse_datetime(removed) if removed else None,
    )


def _sprint(raw: dict) -> Sprint:
    return Sprint(
        id=raw["id"],
        name=raw.get("name") or raw["id"],
        state=raw.get("state") or "active",
        start=parse_date(raw["start"]),
        end=parse_date(raw["end"]),
    )
