"""Сборка результатов. История приходит объектом, каталог слепков не открывается."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from dashboard.config.model import TeamConfig
from dashboard.metrics.cards import (
    blocker_metric,
    blocker_reasons,
    burndown_metric,
    hygiene_metric,
    person_load,
    project_list,
    story_points_coverage,
)
from dashboard.metrics.classify import classification_metric
from dashboard.metrics.cycle import cycle_metrics
from dashboard.metrics.flow import flow_metrics
from dashboard.metrics.hours import status_hours
from dashboard.metrics.parse import Bundle, Issue
from dashboard.metrics.results import Metric
from dashboard.metrics.select import SprintSet, changes_for, rule_at, scope_name, sprint_set, status_at
from dashboard.metrics.time import local_date


@dataclass(frozen=True)
class HistoryPoint:
    as_of_date: date
    sprint_id: str
    snapshot_id: str
    by_role: dict


@dataclass(frozen=True)
class History:
    points: tuple[HistoryPoint, ...] = ()
    previous: HistoryPoint | None = None


@dataclass
class Computed:
    sprint_metrics: list[Metric]
    period_metrics: list[Metric]
    issues: list[dict]
    trend: dict
    coverage: dict
    sprint_id: str
    sprint_start: date
    sprint_end: date
    period_id: str
    period_start: date
    period_end: date
    as_of: datetime
    timezone: str


def compute(bundle: Bundle, config: TeamConfig, *, as_of: datetime | None = None, history: History | None = None) -> Computed:
    moment = as_of or bundle.as_of
    history = history or History()
    sprint = sprint_set(bundle, config)
    flow = flow_metrics(bundle, config, sprint, moment)
    by_role = flow[0].detail["byRole"]
    points = story_points_coverage(config, sprint)
    sprint_metrics = [
        *cycle_metrics(bundle, config, sprint, moment),
        *flow,
        hygiene_metric(bundle, config, sprint, moment),
        blocker_metric(bundle, config, sprint, moment),
        person_load(bundle, config, sprint, moment),
        burndown_metric(bundle, config, sprint, moment, points),
    ]
    classified = classification_metric(bundle, config, moment)
    period_metrics = [
        classified,
        status_hours(bundle, config, moment),
        project_list(bundle, config),
    ]
    return Computed(
        sprint_metrics=sprint_metrics,
        period_metrics=period_metrics,
        issues=[_issue_row(issue, membership, bundle, config, sprint, moment) for issue, membership in sprint.rows],
        trend=_trend(history, sprint, moment, config, by_role),
        coverage=_coverage(bundle, config, sprint, moment, points, classified.value),
        sprint_id=sprint.sprint.id,
        sprint_start=sprint.sprint.start,
        sprint_end=sprint.sprint.end,
        period_id=config.period_id,
        period_start=config.period_start,
        period_end=config.period_end,
        as_of=moment,
        timezone=config.calendar.timezone,
    )


def _issue_row(issue: Issue, membership, bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime) -> dict:
    changes = changes_for(bundle, issue.id, as_of)
    rule = rule_at(issue, changes, as_of, config)
    reasons = []
    if membership.removed_at is None and rule is not None:
        reasons = blocker_reasons(issue, rule.role, config, as_of)
    member = _member(issue, config)
    points = None if config.story_points_field is None else issue.story_points
    due = issue.due_date.isoformat() if issue.due_date else None
    return {
        "key": issue.key,
        "summary": issue.summary,
        "status": status_at(issue, changes, as_of),
        "assigneeId": member.id if member else issue.assignee_account_id,
        "storyPoints": points,
        "scope": scope_name(membership, sprint.sprint, config.calendar.timezone),
        "blockerReasons": reasons,
        "dueDate": due,
        "closedBeforeDue": _closed_before_due(issue, config.calendar.timezone),
    }


def _closed_before_due(issue: Issue, timezone: str):
    if issue.due_date is None or issue.resolution_at is None:
        return None
    return local_date(issue.resolution_at, timezone) < issue.due_date


def _member(issue: Issue, config: TeamConfig):
    if not issue.assignee_account_id:
        return None
    for member in config.members:
        if config.assignee_key(member) == issue.assignee_account_id:
            return member
    return None


def _coverage(bundle, config, sprint: SprintSet, as_of, points: str, unknown_pct) -> dict:
    timed = 0
    for issue, _membership in sprint.current:
        if changes_for(bundle, issue.id, as_of):
            timed += 1
    total = len(sprint.current)
    if total == 0 or timed == 0:
        timing = "none"
    elif timed == total:
        timing = "full"
    else:
        timing = "partial"
    assigned = 0
    matched = 0
    for issue, _membership in sprint.current:
        if not issue.assignee_account_id:
            continue
        assigned += 1
        if _member(issue, config) is not None:
            matched += 1
    return {
        "timing": timing,
        "unknownPct": unknown_pct,
        "storyPoints": points,
        "assigneeMatchPct": None if assigned == 0 else 100 * matched / assigned,
        "membership": "incomplete" if sprint.incomplete else "complete",
    }


def _trend(history: History, sprint: SprintSet, as_of: datetime, config: TeamConfig, by_role: dict) -> dict:
    today = local_date(as_of, config.calendar.timezone)
    earlier = [
        point
        for point in history.points
        if point.sprint_id == sprint.sprint.id and point.as_of_date != today
    ]
    earlier.sort(key=lambda point: point.as_of_date)
    sparkline = [{"date": point.as_of_date.isoformat(), "done": int(point.by_role["done"])} for point in earlier]
    sparkline.append({"date": today.isoformat(), "done": int(by_role["done"])})
    previous = None
    if history.previous is not None:
        previous = {
            "snapshotId": history.previous.snapshot_id,
            "sprintId": history.previous.sprint_id,
            "byRole": history.previous.by_role,
        }
    return {"previous": previous, "sparkline": sparkline}
