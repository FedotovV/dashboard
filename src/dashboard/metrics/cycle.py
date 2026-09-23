"""cycleTime и waitTime. Цикл — сумма роли active, не спан до закрытия."""

from __future__ import annotations

from datetime import datetime

from dashboard.config.model import TeamConfig
from dashboard.metrics.parse import Bundle, Issue
from dashboard.metrics.results import Metric
from dashboard.metrics.select import SprintSet, changes_for, clip_end, rule_at
from dashboard.metrics.time import nominal_seconds, work_seconds


def cycle_metrics(bundle: Bundle, config: TeamConfig, sprint: SprintSet, as_of: datetime) -> list[Metric]:
    nominal = nominal_seconds(config.calendar)
    params = {"minStaySeconds": config.min_stay_seconds, "nominalSeconds": nominal}
    active = _role_metric("cycleTime", "active", bundle, config, sprint, as_of, nominal, params)
    waiting = _role_metric("waitTime", "wait", bundle, config, sprint, as_of, nominal, params)
    return [active, waiting]


def _role_metric(
    metric_id: str,
    role: str,
    bundle: Bundle,
    config: TeamConfig,
    sprint: SprintSet,
    as_of: datetime,
    nominal: int,
    params: dict,
) -> Metric:
    population: list[str] = []
    excluded: list[dict] = []
    per_issue: list[dict] = []
    seconds: list[int] = []
    no_timing = 0
    for issue, _membership in sprint.current:
        rule = rule_at(issue, changes_for(bundle, issue.id, as_of), as_of, config)
        if rule is None or rule.category != "done":
            continue
        outcome = _seconds(issue, role, bundle, config, as_of)
        if outcome is None:
            no_timing += 1
            excluded.append({"issueKey": issue.key, "reason": "no-timing"})
            continue
        total, only_short = outcome
        if only_short:
            excluded.append({"issueKey": issue.key, "reason": "shorter-than-min-stay"})
            continue
        population.append(issue.key)
        seconds.append(total)
        per_issue.append({"issueKey": issue.key, "seconds": total})
    value = None
    if population and no_timing <= len(population):
        value = _median(seconds) / nominal
    return Metric(
        id=metric_id,
        unit="workdays",
        value=value,
        population=population,
        excluded=excluded,
        params=params,
        detail={"perIssue": per_issue},
    )


def _seconds(
    issue: Issue,
    role: str,
    bundle: Bundle,
    config: TeamConfig,
    as_of: datetime,
) -> tuple[int, bool] | None:
    changes = changes_for(bundle, issue.id, as_of)
    if not changes:
        return None
    limit = _close_at(changes, config, as_of)
    total = 0
    kept = False
    saw_short = False
    for change in changes:
        rule = config.status(change.status)
        if rule is None or rule.role != role:
            continue
        stay_end = clip_end(change, as_of)
        if (stay_end - change.entered_at).total_seconds() < config.min_stay_seconds:
            saw_short = True
            continue
        start = change.entered_at
        end = min(stay_end, limit)
        if end <= start:
            continue
        total += work_seconds(start, end, config.calendar)
        kept = True
    if not kept and saw_short:
        return 0, True
    return total, False


def _close_at(changes, config: TeamConfig, as_of: datetime) -> datetime:
    """Пока задача в terminal, цикл кончается на входе в это пребывание.

    Выход из terminal снимает границу: тогда сумма идёт до asOf.
    """
    current = config.status(changes[-1].status)
    if current is not None and current.role == "terminal":
        return changes[-1].entered_at
    return as_of


def _median(values: list[int]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2
