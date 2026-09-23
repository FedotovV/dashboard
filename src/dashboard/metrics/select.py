"""Отбор задач спринта. Роль берётся из statusMap, не из имени статуса."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dashboard.config.model import StatusRule, TeamConfig
from dashboard.metrics.parse import Bundle, Issue, Membership, Sprint, StatusChange
from dashboard.metrics.time import local_date


@dataclass
class SprintSet:
    sprint: Sprint
    rows: list[tuple[Issue, Membership]]
    current: list[tuple[Issue, Membership]]
    incomplete: bool


def in_scope(issue: Issue, config: TeamConfig) -> bool:
    if issue.type not in config.scope.issue_types:
        return False
    if config.scope.project_keys is not None and issue.project_key not in config.scope.project_keys:
        return False
    if issue.subtask and not config.scope.count_subtasks:
        return False
    return True


def sprint_set(bundle: Bundle, config: TeamConfig) -> SprintSet:
    sprint = _sprint(bundle, config)
    by_id = {issue.id: issue for issue in bundle.issues}
    rows: list[tuple[Issue, Membership]] = []
    incomplete = False
    for membership in bundle.memberships:
        if membership.sprint_id != sprint.id:
            continue
        issue = by_id.get(membership.issue_id)
        if issue is None or not in_scope(issue, config):
            continue
        if membership.added_at is None:
            incomplete = True
        rows.append((issue, membership))
    rows.sort(key=lambda item: item[0].key)
    current = [(issue, membership) for issue, membership in rows if membership.removed_at is None]
    return SprintSet(sprint=sprint, rows=rows, current=current, incomplete=incomplete)


def _sprint(bundle: Bundle, config: TeamConfig) -> Sprint:
    if config.sprint_id:
        for sprint in bundle.sprints:
            if sprint.id == config.sprint_id:
                return sprint
        raise ValueError(f"в bundle нет спринта {config.sprint_id}")
    active = [sprint for sprint in bundle.sprints if sprint.state == "active"]
    if len(active) == 1:
        return active[0]
    raise ValueError("для build нужен sprintId")


def changes_for(bundle: Bundle, issue_id: str, as_of: datetime) -> list[StatusChange]:
    rows = [
        change
        for change in bundle.status_changes
        if change.issue_id == issue_id and change.entered_at <= as_of
    ]
    rows.sort(key=lambda change: change.entered_at)
    return rows


def status_at(issue: Issue, changes: list[StatusChange], as_of: datetime) -> str:
    if changes:
        return changes[-1].status
    return issue.status


def rule_at(issue: Issue, changes: list[StatusChange], as_of: datetime, config: TeamConfig) -> StatusRule | None:
    return config.status(status_at(issue, changes, as_of))


def scope_name(membership: Membership, sprint: Sprint, timezone: str) -> str:
    if membership.removed_at is not None:
        return "removed"
    if membership.added_at is None:
        return "added"
    added = local_date(membership.added_at, timezone)
    if added <= sprint.start:
        return "committed"
    return "added"


def clip_end(change: StatusChange, as_of: datetime) -> datetime:
    if change.exited_at is None or change.exited_at > as_of:
        return as_of
    return change.exited_at
