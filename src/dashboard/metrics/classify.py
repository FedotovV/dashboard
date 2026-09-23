"""Классификация: голова эпика, затем правило, затем явная метка, иначе unknown."""

from __future__ import annotations

from collections import deque
from datetime import datetime

from dashboard.config.model import TeamConfig
from dashboard.metrics.parse import Bundle, Issue
from dashboard.metrics.results import Metric
from dashboard.metrics.select import changes_for, in_scope
from dashboard.metrics.time import local_date

BLOCKED = {"blocks", "block", "блокировка"}


def classification_metric(bundle: Bundle, config: TeamConfig, as_of: datetime) -> Metric:
    children = _children(bundle, config)
    heads = _heads(bundle, config)
    reached = {head_id: _walk(head_id, children) for head_id, _category in heads}
    paths = []
    unknown = 0
    for issue in _period_issues(bundle, config, as_of):
        path = _classify(issue, heads, reached, config)
        paths.append(path)
        if path["reason"] == "unknown":
            unknown += 1
    total = len(paths)
    percent = None if total == 0 else 100 * unknown / total
    warnings = []
    if percent is not None and percent > config.unknown_warn_pct:
        warnings.append("unknown-above-threshold")
    return Metric(
        id="classification",
        unit="percent",
        value=percent,
        population=[path["issueKey"] for path in paths if path["reason"] != "unknown"],
        excluded=[
            {"issueKey": path["issueKey"], "reason": "unknown"}
            for path in paths
            if path["reason"] == "unknown"
        ],
        warnings=warnings,
        params={"unknownWarnPct": config.unknown_warn_pct},
        detail={"paths": paths},
    )


def _children(bundle: Bundle, config: TeamConfig) -> dict[str, list[str]]:
    allowed = set(config.taxonomy.link_types)
    kids: dict[str, list[str]] = {}

    def add(parent: str, child: str) -> None:
        bucket = kids.setdefault(parent, [])
        if child not in bucket:
            bucket.append(child)

    for link in bundle.links:
        if link.type.lower() in BLOCKED or link.type not in allowed:
            continue
        add(link.from_id, link.to_id)
    for issue in bundle.issues:
        if issue.parent_id:
            add(issue.parent_id, issue.id)
    return kids


def _heads(bundle: Bundle, config: TeamConfig) -> list[tuple[str, str]]:
    by_key = {issue.key: issue for issue in bundle.issues}
    found = []
    for category in ("project", "tech"):
        for key in config.taxonomy.epics.keys(category):
            issue = by_key.get(key)
            found.append((issue.id if issue else key, category))
    return found


def _walk(head_id: str, children: dict[str, list[str]]) -> dict[str, tuple[int, str]]:
    seen = {head_id}
    queue = deque([(head_id, 0)])
    found: dict[str, tuple[int, str]] = {}
    while queue:
        node, depth = queue.popleft()
        for child in children.get(node, []):
            if child in seen:
                continue
            seen.add(child)
            found[child] = (depth + 1, node)
            queue.append((child, depth + 1))
    return found


def _classify(issue: Issue, heads, reached, config: TeamConfig) -> dict:
    priority = {name: index for index, name in enumerate(config.taxonomy.priority)}
    candidates = []
    for head_id, category in heads:
        if issue.id == head_id:
            candidates.append((0, priority.get(category, 99), head_id, head_id, category))
            continue
        hit = reached[head_id].get(issue.id)
        if hit is None:
            continue
        depth, parent_id = hit
        candidates.append((depth, priority.get(category, 99), parent_id, head_id, category))
    if candidates:
        _depth, _rank, _parent, head_id, category = min(candidates)
        return _path(issue.key, head_id, category, None, "head")
    for rule in config.taxonomy.rules:
        if _rule_matches(rule, issue):
            return _path(issue.key, None, rule.category, None, "rule")
    if config.taxonomy.prod_label and config.taxonomy.prod_label in issue.labels:
        return _path(issue.key, None, "other", "prod", "label")
    if config.taxonomy.tech_label and config.taxonomy.tech_label in issue.labels:
        return _path(issue.key, None, "other", "tech", "label")
    return _path(issue.key, None, "unknown", None, "unknown")


def _rule_matches(rule, issue: Issue) -> bool:
    if rule.label is None and rule.project_key is None:
        return False
    if rule.label is not None and rule.label not in issue.labels:
        return False
    if rule.project_key is not None and rule.project_key != issue.project_key:
        return False
    return True


def _path(key: str, head_id: str | None, category: str, subtype: str | None, reason: str) -> dict:
    return {
        "issueKey": key,
        "headId": head_id,
        "category": category,
        "subtype": subtype,
        "reason": reason,
    }


def _period_issues(bundle: Bundle, config: TeamConfig, as_of: datetime) -> list[Issue]:
    timezone = config.calendar.timezone
    today = local_date(as_of, timezone)
    end = min(config.period_end, today)
    selected = []
    for issue in bundle.issues:
        if not in_scope(issue, config):
            continue
        created = local_date(issue.created, timezone)
        first = _first_active(bundle, issue, config, as_of)
        active_on = local_date(first, timezone) if first else None
        created_in = config.period_start <= created <= end
        active_in = active_on is not None and config.period_start <= active_on <= end
        if created_in or active_in:
            selected.append(issue)
    selected.sort(key=lambda issue: issue.key)
    return selected


def _first_active(bundle: Bundle, issue: Issue, config: TeamConfig, as_of: datetime) -> datetime | None:
    moments = []
    for change in changes_for(bundle, issue.id, as_of):
        rule = config.status(change.status)
        if rule is not None and rule.role == "active":
            moments.append(change.entered_at)
    if not moments:
        return None
    return min(moments)
