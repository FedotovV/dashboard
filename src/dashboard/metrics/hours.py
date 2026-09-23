"""Часы в статусе. Это не списание и не цель."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from dashboard.config.model import Member, TeamConfig
from dashboard.metrics.parse import Bundle, Issue
from dashboard.metrics.results import Metric
from dashboard.metrics.select import changes_for, clip_end, in_scope
from dashboard.metrics.time import elapsed_workdays, nominal_seconds, work_seconds


def status_hours(bundle: Bundle, config: TeamConfig, as_of: datetime) -> Metric:
    nominal = nominal_seconds(config.calendar)
    elapsed = elapsed_workdays(config.period_start, config.period_end, as_of, config.calendar)
    params = {"nominalSeconds": nominal}
    if not elapsed:
        return Metric(
            id="statusHours",
            unit="ratio",
            value=None,
            params=params,
            detail={
                "parallelism": None,
                "inheritedSeconds": 0,
                "ownSeconds": 0,
                "days": [],
            },
        )
    tz = ZoneInfo(config.calendar.timezone)
    period_open = datetime.combine(config.period_start, time(0, 0), tzinfo=tz)
    raw_total = 0
    scaled_total = 0
    inherited_total = 0
    capacity = 0
    day_rows: list[dict] = []
    for day in elapsed:
        buckets: dict[str, dict] = {}
        for issue in bundle.issues:
            if not in_scope(issue, config) or not issue.assignee_account_id:
                continue
            member = _member(issue, config)
            if member is not None and not _on_roster(member, day):
                continue
            raw = _active_seconds(issue, bundle, config, as_of, day)
            if raw <= 0:
                continue
            person_id = member.id if member else issue.assignee_account_id
            first = _first_active(issue, bundle, config, as_of)
            inherited = first is not None and first < period_open
            bucket = buckets.setdefault(
                person_id,
                {"outside": member is None, "allocation": 1 if member is None else member.allocation, "parts": []},
            )
            bucket["parts"].append({"key": issue.key, "raw": raw, "inherited": inherited})
        for member in config.members:
            if _on_roster(member, day):
                capacity += int(round(nominal * member.allocation))
        for person_id, bucket in buckets.items():
            raws = [part["raw"] for part in bucket["parts"]]
            limit = int(round(nominal * bucket["allocation"]))
            scaled_parts = _scale(raws, limit)
            raw_sum = sum(raws)
            scaled_sum = sum(scaled_parts)
            inherited = sum(
                scaled
                for part, scaled in zip(bucket["parts"], scaled_parts)
                if part["inherited"]
            )
            own = scaled_sum - inherited
            raw_total += raw_sum
            scaled_total += scaled_sum
            inherited_total += inherited
            day_rows.append(
                {
                    "personId": person_id,
                    "date": day.isoformat(),
                    "rawSeconds": raw_sum,
                    "scaledSeconds": scaled_sum,
                    "inheritedSeconds": inherited,
                    "ownSeconds": own,
                    "outside": bucket["outside"],
                }
            )
    own_total = scaled_total - inherited_total
    ratio = None if capacity == 0 else scaled_total / capacity
    parallelism = None if scaled_total == 0 else raw_total / scaled_total
    return Metric(
        id="statusHours",
        unit="ratio",
        value=ratio,
        params=params,
        detail={
            "parallelism": parallelism,
            "inheritedSeconds": inherited_total,
            "ownSeconds": own_total,
            "days": day_rows,
        },
    )


def _active_seconds(issue: Issue, bundle: Bundle, config: TeamConfig, as_of: datetime, day) -> int:
    total = 0
    for change in changes_for(bundle, issue.id, as_of):
        rule = config.status(change.status)
        if rule is None or rule.role != "active":
            continue
        end = clip_end(change, as_of)
        if end <= change.entered_at:
            continue
        total += _on_day(change.entered_at, end, day, config)
    return total


def _on_day(start: datetime, end: datetime, day, config: TeamConfig) -> int:
    tz = ZoneInfo(config.calendar.timezone)
    day_start = datetime.combine(day, time(0, 0), tzinfo=tz)
    day_end = day_start.replace(hour=0) + _one_day()
    left = max(start, day_start)
    right = min(end, day_end)
    if right <= left:
        return 0
    return work_seconds(left, right, config.calendar)


def _one_day():
    from datetime import timedelta

    return timedelta(days=1)


def _first_active(issue: Issue, bundle: Bundle, config: TeamConfig, as_of: datetime) -> datetime | None:
    moments = [
        change.entered_at
        for change in changes_for(bundle, issue.id, as_of)
        if (rule := config.status(change.status)) is not None and rule.role == "active"
    ]
    if not moments:
        return None
    return min(moments)


def _scale(parts: list[int], limit: int) -> list[int]:
    raw = sum(parts)
    if raw == 0 or limit <= 0 or raw <= limit:
        return list(parts)
    scaled = [part * limit // raw for part in parts]
    leftover = limit - sum(scaled)
    order = sorted(
        range(len(parts)),
        key=lambda index: (parts[index] * limit % raw, parts[index]),
        reverse=True,
    )
    for index in order[:leftover]:
        scaled[index] += 1
    return scaled


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
