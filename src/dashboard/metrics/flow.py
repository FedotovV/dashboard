"""Состав спринта: роли, движение состава, завершение к старту."""

from __future__ import annotations

from datetime import datetime

from dashboard.config.model import TeamConfig
from dashboard.metrics.parse import Bundle
from dashboard.metrics.results import Metric
from dashboard.metrics.select import SprintSet, changes_for, rule_at, scope_name

ROLES = ("active", "wait", "hold", "queue", "done", "canceled")


def flow_metrics(bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime) -> list[Metric]:
    counts, population, excluded = _counts(bundle, config, sprint, as_of)
    flow = Metric(
        id="sprintFlow",
        unit="issues",
        value=counts["total"],
        population=population,
        excluded=excluded,
        params={},
        detail={"byRole": counts},
    )
    scope = _scope(config, sprint)
    completion = _completion(bundle, config, sprint, as_of, scope)
    return [flow, scope, completion]


def _counts(bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime):
    counts = {role: 0 for role in (*ROLES, "total")}
    population: list[str] = []
    excluded: list[dict] = []
    for issue, _membership in sprint.current:
        changes = changes_for(bundle, issue.id, as_of)
        rule = rule_at(issue, changes, as_of, config)
        if rule is None:
            excluded.append({"issueKey": issue.key, "reason": "unknown-status"})
            continue
        if rule.role == "terminal" and rule.outcome == "canceled":
            counts["canceled"] += 1
        elif rule.role == "terminal":
            counts["done"] += 1
        else:
            counts[rule.role] += 1
        population.append(issue.key)
    counts["total"] = sum(counts[role] for role in ROLES)
    return counts, population, excluded


def _scope(config: TeamConfig, sprint: SprintSet) -> Metric:
    groups = {"committed": [], "added": [], "removed": []}
    for issue, membership in sprint.rows:
        groups[scope_name(membership, sprint.sprint, config.calendar.timezone)].append(issue.key)
    if sprint.incomplete:
        detail = {"committed": None, "added": None, "removed": None}
    else:
        detail = {
            "committed": len(groups["committed"]),
            "added": len(groups["added"]),
            "removed": len(groups["removed"]),
            "committedKeys": groups["committed"],
            "addedKeys": groups["added"],
            "removedKeys": groups["removed"],
        }
    return Metric(
        id="scopeChange",
        unit="issues",
        value=None,
        population=[*groups["committed"], *groups["added"], *groups["removed"]],
        params={},
        detail=detail,
    )


def _completion(
    bundle: Bundle,
    config: TeamConfig,
    sprint: SprintSet,
    as_of: datetime,
    scope: Metric,
) -> Metric:
    detail = scope.detail or {}
    committed = detail.get("committed")
    if sprint.incomplete or not committed:
        return Metric(
            id="completionVsCommitted",
            unit="ratio",
            value=None,
            params={},
            detail={"done": None, "committed": committed},
        )
    done = 0
    keys: list[str] = []
    for issue, membership in sprint.rows:
        if scope_name(membership, sprint.sprint, config.calendar.timezone) != "committed":
            continue
        rule = rule_at(issue, changes_for(bundle, issue.id, as_of), as_of, config)
        if rule is not None and rule.role == "terminal" and rule.outcome != "canceled":
            done += 1
            keys.append(issue.key)
    return Metric(
        id="completionVsCommitted",
        unit="ratio",
        value=done / committed,
        population=keys,
        params={},
        detail={"done": done, "committed": committed},
    )
