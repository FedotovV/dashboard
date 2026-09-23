"""Короткие фикстуры тестов. Числа в тестах посчитаны по каталогу, не сняты с прогона."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from dashboard.config.model import (
    Calendar,
    Epics,
    Member,
    Scope,
    StatusRule,
    Taxonomy,
    TeamConfig,
)
from dashboard.metrics.parse import Bundle, Issue, Link, Membership, Sprint, StatusChange


def at(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        return instant.replace(tzinfo=timezone.utc)
    return instant


def calendar(**kwargs) -> Calendar:
    raw = dict(
        timezone="Europe/Moscow",
        workdays=(1, 2, 3, 4, 5),
        work_start=time(10, 0),
        work_end=time(19, 0),
        break_minutes=60,
        break_start=time(14, 0),
        hours_per_day=8,
        holidays=frozenset(),
        extra_workdays=frozenset(),
    )
    raw.update(kwargs)
    return Calendar(**raw)


def member(person_id: str = "dev", **kwargs) -> Member:
    raw = dict(
        id=person_id,
        name=person_id,
        jira_username=person_id,
        jira_account_id=None,
        role="dev",
        allocation=1,
        feature_lead_of=(),
        active_from=None,
        active_to=None,
        absences=(),
    )
    raw.update(kwargs)
    return Member(**raw)


def status_map() -> tuple[StatusRule, ...]:
    return (
        StatusRule("To Do", "todo", "queue", "completed"),
        StatusRule("In Progress", "indeterminate", "active", "completed"),
        StatusRule("Review", "indeterminate", "wait", "completed"),
        StatusRule("On-hold", "indeterminate", "hold", "completed"),
        StatusRule("Done", "done", "terminal", "completed"),
        StatusRule("Canceled", "done", "terminal", "canceled"),
    )


def team(**kwargs) -> TeamConfig:
    raw = dict(
        version=1,
        catalog_version=1,
        team_id="card",
        team_name="Карта",
        members=(member(),),
        alumni=(),
        calendar=calendar(),
        period_id="2026-09",
        period_start=date(2026, 9, 7),
        period_end=date(2026, 9, 30),
        deployment="server",
        sprint_id="s",
        auth_env="JIRA_TOKEN",
        story_points_field="customfield_10016",
        uses_due_date=True,
        status_map=status_map(),
        taxonomy=Taxonomy(
            priority=("project", "tech"),
            epics=Epics(project=("P-1",), tech=("T-1",)),
            link_types=("Child-Issue",),
            rules=(),
            prod_label="prod_op",
            tech_label="other_tech",
        ),
        scope=Scope(issue_types=frozenset({"Story", "Task", "Bug"}), project_keys=frozenset({"CARD"}), count_subtasks=False),
        min_stay_seconds=900,
        high_priorities=("High",),
        max_age_days=90,
        unknown_warn_pct=15,
        raw_calendar={},
        raw_workflow={},
        raw_taxonomy={},
        raw_scope={},
    )
    raw.update(kwargs)
    return TeamConfig(**raw)


def issue(key: str, **kwargs) -> Issue:
    raw = dict(
        id=key,
        key=key,
        summary=key,
        type="Story",
        project_key="CARD",
        status="In Progress",
        created=at("2026-09-07T07:00:00Z"),
        assignee_account_id="dev",
        priority=None,
        story_points=None,
        story_points_at_add=None,
        due_date=None,
        resolution_at=None,
        labels=(),
        parent_id=None,
        subtask=False,
    )
    raw.update(kwargs)
    return Issue(**raw)


def change(issue_id: str, status: str, entered: str, exited: str | None = None) -> StatusChange:
    return StatusChange(
        issue_id=issue_id,
        status=status,
        entered_at=at(entered),
        exited_at=at(exited) if exited else None,
    )


def membership(issue_id: str, added: str = "2026-09-07T06:00:00Z", removed: str | None = None, sprint_id: str = "s") -> Membership:
    return Membership(
        issue_id=issue_id,
        sprint_id=sprint_id,
        added_at=at(added) if added else None,
        removed_at=at(removed) if removed else None,
    )


def sprint(**kwargs) -> Sprint:
    raw = dict(id="s", name="Спринт", state="active", start=date(2026, 9, 7), end=date(2026, 9, 18))
    raw.update(kwargs)
    return Sprint(**raw)


def bundle(issues: list[Issue], changes: list[StatusChange] | None = None, memberships: list[Membership] | None = None, **kwargs) -> Bundle:
    rows = tuple(memberships if memberships is not None else [membership(item.id) for item in issues])
    raw = dict(
        bundle_id="b",
        as_of=at("2026-09-09T16:00:00Z"),
        source_watermark="test",
        issues=tuple(issues),
        status_changes=tuple(changes or []),
        memberships=rows,
        sprints=(sprint(),),
        links=(),
    )
    raw.update(kwargs)
    return Bundle(**raw)


def link(parent: str, child: str, link_type: str = "Child-Issue") -> Link:
    return Link(from_id=parent, to_id=child, type=link_type)
