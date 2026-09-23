"""YAML → TeamConfig. Окно дня и версия каталога проверяются здесь."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker

from dashboard.config.model import (
    Absence,
    Calendar,
    Epics,
    Member,
    Rule,
    Scope,
    StatusRule,
    Taxonomy,
    TeamConfig,
)

ROOT = Path(__file__).resolve().parents[3]
TEAM_SCHEMA = ROOT / "schema" / "team.schema.json"
CATALOG_VERSION = 1
METRIC_VERSIONS = {"cycleTime": 1, "hygiene": 1, "classification": 1}


class ConfigError(ValueError):
    """team.yaml нельзя считать."""


def load_team(path: Path) -> TeamConfig:
    raw = yaml.safe_load(Path(path).read_text())
    data = _jsonable(raw)
    schema = json.loads(TEAM_SCHEMA.read_text())
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ConfigError(errors[0].message)
    _reject_versions(data)
    calendar = _calendar(data["calendar"])
    _reject_window(data["calendar"], calendar)
    return _build(data, calendar)


def _jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _reject_versions(data: dict) -> None:
    if data["catalogVersion"] != CATALOG_VERSION:
        raise ConfigError(f"неизвестная catalogVersion {data['catalogVersion']}")
    for metric_id, body in (data.get("metrics") or {}).items():
        version = (body or {}).get("version", 1)
        expected = METRIC_VERSIONS.get(metric_id)
        if expected is None or version != expected:
            raise ConfigError(f"неизвестная версия формулы {metric_id}={version}")


def _clock(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _calendar(raw: dict) -> Calendar:
    start = _clock(raw["workStart"])
    end = _clock(raw["workEnd"])
    minutes = int(raw.get("breakMinutes") or 0)
    break_start = _resolve_break(start, end, minutes, raw.get("breakStart"))
    return Calendar(
        timezone=raw["timezone"],
        workdays=tuple(raw["workdays"]),
        work_start=start,
        work_end=end,
        break_minutes=minutes,
        break_start=break_start,
        hours_per_day=raw["hoursPerDay"],
        holidays=frozenset(_dates(raw.get("holidays") or [])),
        extra_workdays=frozenset(_dates(raw.get("extraWorkdays") or [])),
    )


def _resolve_break(start: time, end: time, minutes: int, break_start: str | None) -> time | None:
    if minutes <= 0:
        return None
    start_m = _minutes(start)
    end_m = _minutes(end)
    if break_start:
        at = _minutes(_clock(break_start))
    else:
        at = start_m + ((end_m - start_m) - minutes) // 2
    if at < start_m or at + minutes > end_m:
        raise ConfigError("перерыв выходит за рабочее окно")
    return time(at // 60, at % 60)


def _reject_window(raw: dict, calendar: Calendar) -> None:
    start = _minutes(calendar.work_start)
    end = _minutes(calendar.work_end)
    if end <= start:
        raise ConfigError("workEnd должен быть позже workStart")
    hours = (end - start - calendar.break_minutes) / 60
    if abs(hours - calendar.hours_per_day) > 1e-9:
        raise ConfigError("длина окна минус перерыв не равна hoursPerDay")
    if set(raw.get("holidays") or []) & set(raw.get("extraWorkdays") or []):
        raise ConfigError("дата одновременно праздник и рабочий день")


def _dates(values: list) -> list[date]:
    return [date.fromisoformat(value) for value in values]


def _member(raw: dict) -> Member:
    return Member(
        id=raw["id"],
        name=raw["name"],
        jira_username=raw.get("jiraUsername"),
        jira_account_id=raw.get("jiraAccountId"),
        role=raw.get("role"),
        allocation=raw.get("allocation", 1),
        feature_lead_of=tuple(raw.get("featureLeadOf") or []),
        active_from=_maybe_date(raw.get("activeFrom")),
        active_to=_maybe_date(raw.get("activeTo")),
        absences=tuple(
            Absence(start=date.fromisoformat(item["start"]), end=date.fromisoformat(item["end"]))
            for item in raw.get("absences") or []
        ),
    )


def _maybe_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _build(data: dict, calendar: Calendar) -> TeamConfig:
    metrics = data.get("metrics") or {}
    cycle = metrics.get("cycleTime") or {}
    hygiene = metrics.get("hygiene") or {}
    classification = metrics.get("classification") or {}
    taxonomy = data["taxonomy"]
    other = taxonomy.get("otherSubtype") or {}
    fields = (data["sources"].get("jira") or {}).get("fields") or {}
    story_points = fields.get("storyPoints")
    return TeamConfig(
        version=data["version"],
        catalog_version=data["catalogVersion"],
        team_id=data["team"]["id"],
        team_name=data["team"]["name"],
        members=tuple(_member(item) for item in data["team"]["members"]),
        alumni=tuple(_member(item) for item in data["team"].get("alumni") or []),
        calendar=calendar,
        period_id=data["period"]["id"],
        period_start=date.fromisoformat(data["period"]["start"]),
        period_end=date.fromisoformat(data["period"]["end"]),
        deployment=data["sources"]["jira"]["deployment"],
        sprint_id=(data["sources"]["jira"].get("sprintId") or None),
        auth_env=data["sources"]["jira"].get("authEnv"),
        story_points_field=story_points if story_points else None,
        uses_due_date=data["workflow"]["usesDueDate"],
        status_map=tuple(
            StatusRule(
                status=row["status"],
                category=row["category"],
                role=row["role"],
                outcome=row.get("outcome", "completed"),
            )
            for row in data["workflow"]["statusMap"]
        ),
        taxonomy=Taxonomy(
            priority=tuple(taxonomy["priority"]),
            epics=Epics(
                project=tuple(taxonomy["epics"]["project"]),
                tech=tuple(taxonomy["epics"]["tech"]),
            ),
            link_types=tuple(taxonomy.get("linkTypes") or ["Child-Issue"]),
            rules=tuple(
                Rule(
                    category=rule["category"],
                    label=(rule.get("when") or {}).get("label"),
                    project_key=(rule.get("when") or {}).get("projectKey"),
                )
                for rule in taxonomy.get("rules") or []
            ),
            prod_label=other.get("prodLabel"),
            tech_label=other.get("techLabel"),
        ),
        scope=Scope(
            issue_types=frozenset(data["scope"]["issueTypes"]),
            project_keys=(
                frozenset(data["scope"]["projectKeys"])
                if data["scope"].get("projectKeys") is not None
                else None
            ),
            count_subtasks=data["scope"]["countSubtasks"],
        ),
        min_stay_seconds=int(cycle.get("minStaySeconds", 900)),
        high_priorities=tuple(hygiene.get("highPriorities") or []),
        max_age_days=int(hygiene.get("maxAgeDays", 90)),
        unknown_warn_pct=float(classification.get("unknownWarnPct", 15)),
        raw_calendar=data["calendar"],
        raw_workflow=data["workflow"],
        raw_taxonomy=data["taxonomy"],
        raw_scope=data["scope"],
    )
