"""Гигиена, блокеры, люди, burndown и список эпиков."""

from __future__ import annotations

from datetime import datetime

from dashboard.config.model import Member, TeamConfig
from dashboard.metrics.parse import Bundle, Issue
from dashboard.metrics.results import Metric
from dashboard.metrics.ru_calendar import chart_days
from dashboard.metrics.select import SprintSet, changes_for, rule_at, status_at
from dashboard.metrics.time import local_date

BLOCKER_RANK = {"overdue": 0, "hold": 1, "no-assignee": 2}


def hygiene_metric(bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime) -> Metric:
    items = []
    excluded = []
    for issue, _membership in sprint.current:
        changes = changes_for(bundle, issue.id, as_of)
        rule = rule_at(issue, changes, as_of, config)
        if rule is None:
            excluded.append({"issueKey": issue.key, "reason": "unknown-status"})
            continue
        reason = _hygiene_reason(issue, rule.role, config, as_of)
        if reason:
            items.append({"issueKey": issue.key, "reason": reason})
    return Metric(
        id="hygiene",
        unit="issues",
        value=len(items),
        population=[item["issueKey"] for item in items],
        excluded=excluded,
        params={"maxAgeDays": config.max_age_days},
        detail={"items": items},
    )


def _hygiene_reason(issue: Issue, role: str, config: TeamConfig, as_of: datetime) -> str | None:
    if config.story_points_field and issue.story_points is None:
        return "no-story-points"
    if role == "active" and not issue.assignee_account_id:
        return "no-assignee"
    if config.uses_due_date and role != "terminal" and issue.due_date is None:
        return "no-due-date"
    if role == "queue" and issue.priority in config.high_priorities:
        return "high-priority-queue"
    age_days = (local_date(as_of, config.calendar.timezone) - local_date(issue.created, config.calendar.timezone)).days
    if role != "terminal" and age_days > config.max_age_days:
        return "too-old"
    return None


def blocker_metric(bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime) -> Metric:
    today = local_date(as_of, config.calendar.timezone)
    items = []
    for issue, _membership in sprint.current:
        changes = changes_for(bundle, issue.id, as_of)
        rule = rule_at(issue, changes, as_of, config)
        if rule is None:
            continue
        reasons = _blocker_reasons(issue, rule.role, config, today)
        if reasons:
            items.append({"issueKey": issue.key, "reasons": reasons})
    items.sort(key=lambda item: (BLOCKER_RANK[item["reasons"][0]], item["issueKey"]))
    return Metric(
        id="blockers",
        unit="issues",
        value=len(items),
        population=[item["issueKey"] for item in items],
        params={},
        detail={"items": items},
    )


def blocker_reasons(issue: Issue, role: str, config: TeamConfig, as_of: datetime) -> list[str]:
    today = local_date(as_of, config.calendar.timezone)
    return _blocker_reasons(issue, role, config, today)


def _blocker_reasons(issue: Issue, role: str, config: TeamConfig, today) -> list[str]:
    reasons = []
    if (
        config.uses_due_date
        and issue.due_date is not None
        and issue.due_date < today
        and role != "terminal"
    ):
        reasons.append("overdue")
    if role == "hold":
        reasons.append("hold")
    if role == "active" and not issue.assignee_account_id:
        reasons.append("no-assignee")
    reasons.sort(key=lambda reason: BLOCKER_RANK[reason])
    return reasons


def person_load(bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime) -> Metric:
    today = local_date(as_of, config.calendar.timezone)
    rows = []
    for member in config.members:
        if not _on_roster(member, today):
            continue
        rows.append(_person_row(bundle, config, sprint, as_of, member))
    return Metric(
        id="personLoad",
        unit="people",
        value=len(rows),
        population=[row["personId"] for row in rows],
        params={},
        detail={"rows": rows},
    )


def _person_row(bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime, member: Member) -> dict:
    counts = {"backlog": 0, "inProgress": 0, "paused": 0, "testing": 0, "done": 0, "canceled": 0, "unknown": 0}
    keys = []
    issues = []
    points = 0.0
    open_points = 0.0
    points_missing = 0
    for issue, _membership in sprint.current:
        if _member(issue, config) != member:
            continue
        changes = changes_for(bundle, issue.id, as_of)
        rule = rule_at(issue, changes, as_of, config)
        role = None if rule is None else rule.role
        bucket = _person_bucket(rule)
        counts[bucket] += 1
        if rule is not None and rule.role != "terminal":
            keys.append(issue.key)
        story_points = None if config.story_points_field is None else issue.story_points
        if config.story_points_field is not None and story_points is None:
            points_missing += 1
        if isinstance(story_points, (int, float)) and not isinstance(story_points, bool):
            points += story_points
            if role != "terminal":
                open_points += story_points
        issues.append(
            {
                "key": issue.key,
                "summary": issue.summary,
                "status": status_at(issue, changes, as_of),
                "role": role,
                "storyPoints": story_points,
            }
        )
    return {
        "personId": member.id,
        "name": member.name,
        "openKeys": keys,
        "total": len(issues),
        "backlog": counts["backlog"],
        "inProgress": counts["inProgress"],
        "paused": counts["paused"],
        "testing": counts["testing"],
        "done": counts["done"],
        "canceled": counts["canceled"],
        "unknown": counts["unknown"],
        "storyPoints": None if config.story_points_field is None else points,
        "openStoryPoints": None if config.story_points_field is None else open_points,
        "pointsMissing": points_missing,
        "issues": issues,
    }


def _person_bucket(rule) -> str:
    if rule is None:
        return "unknown"
    if rule.role == "queue":
        return "backlog"
    if rule.role == "active":
        return "inProgress"
    if rule.role == "hold":
        return "paused"
    if rule.role == "wait":
        return "testing"
    if rule.role == "terminal":
        return "canceled" if rule.outcome == "canceled" else "done"
    return "unknown"


def burndown_metric(
    bundle: Bundle,
    config: TeamConfig,
    sprint: SprintSet,
    as_of: datetime,
    story_points: str,
) -> Metric:
    if story_points != "full":
        return Metric(id="burndown", unit="points", value=None, params={}, detail={"points": []})
    total = sum(issue.story_points_at_add or 0 for issue, _membership in sprint.current)
    burned: list[tuple] = []
    for issue, _membership in sprint.current:
        changes = changes_for(bundle, issue.id, as_of)
        rule = rule_at(issue, changes, as_of, config)
        if rule is None or rule.role != "terminal" or not changes:
            continue
        burned.append(
            (local_date(changes[-1].entered_at, config.calendar.timezone), issue.story_points_at_add or 0)
        )
    today = local_date(as_of, config.calendar.timezone)
    last = min(sprint.sprint.end, today)
    workdays = chart_days(sprint.sprint.start, sprint.sprint.end, config.calendar)
    steps = len(workdays) - 1
    points = []
    for index, day in enumerate(workdays):
        if day > last:
            break
        fraction = 0 if steps <= 0 else index / steps
        burned_sum = sum(points_at for when, points_at in burned if when <= day)
        points.append(
            {
                "date": day.isoformat(),
                "ideal": total * (1 - fraction),
                "actual": total - burned_sum,
            }
        )
    value = total if not points else points[-1]["actual"]
    return Metric(
        id="burndown",
        unit="points",
        value=value,
        params={"storyPointsAtAdd": total},
        detail={"points": points},
    )


def project_list(bundle: Bundle, config: TeamConfig) -> Metric:
    by_key = {issue.key: issue for issue in bundle.issues}
    rows = []
    for category in config.taxonomy.priority:
        for key in config.taxonomy.epics.keys(category):
            issue = by_key.get(key)
            lead = next((member.id for member in config.members if key in member.feature_lead_of), None)
            rows.append(
                {
                    "key": key,
                    "name": issue.summary if issue else key,
                    "status": issue.status if issue else None,
                    "featureLead": lead,
                    "release": None,
                    "note": None,
                }
            )
    warnings = ["no-epics"] if not rows else []
    return Metric(
        id="projectList",
        unit="epics",
        value=len(rows),
        population=[row["key"] for row in rows],
        warnings=warnings,
        params={},
        detail={"rows": rows},
    )


def story_points_coverage(config: TeamConfig, sprint: SprintSet) -> str:
    if config.story_points_field is None:
        return "off"
    if all(issue.story_points_at_add is not None for issue, _membership in sprint.current):
        return "full"
    return "partial"


def _member(issue: Issue, config: TeamConfig) -> Member | None:
    for member in config.members:
        if config.assignee_key(member) and config.assignee_key(member) == issue.assignee_account_id:
            return member
    return None


def _on_roster(member: Member, day) -> bool:
    if member.active_from and day < member.active_from:
        return False
    if member.active_to and day > member.active_to:
        return False
    return not any(item.start <= day <= item.end for item in member.absences)
