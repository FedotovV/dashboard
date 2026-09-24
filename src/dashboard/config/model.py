"""Разобранный team.yaml. Секретов нет: auth_env — только имя переменной."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class Absence:
    start: date
    end: date


@dataclass(frozen=True)
class Member:
    id: str
    name: str
    jira_username: str | None
    jira_account_id: str | None
    role: str | None
    allocation: float
    feature_lead_of: tuple[str, ...]
    active_from: date | None
    active_to: date | None
    absences: tuple[Absence, ...]


@dataclass(frozen=True)
class Calendar:
    timezone: str
    workdays: tuple[int, ...]
    work_start: time
    work_end: time
    break_minutes: int
    break_start: time | None
    hours_per_day: float
    holidays: frozenset[date]
    extra_workdays: frozenset[date]


@dataclass(frozen=True)
class StatusRule:
    status: str
    category: str
    role: str
    outcome: str


@dataclass(frozen=True)
class Rule:
    category: str
    label: str | None
    project_key: str | None


@dataclass(frozen=True)
class Epics:
    project: tuple[str, ...]
    tech: tuple[str, ...]

    def keys(self, category: str) -> tuple[str, ...]:
        return getattr(self, category)


@dataclass(frozen=True)
class Taxonomy:
    priority: tuple[str, ...]
    epics: Epics
    link_types: tuple[str, ...]
    rules: tuple[Rule, ...]
    prod_label: str | None
    tech_label: str | None


@dataclass(frozen=True)
class Scope:
    issue_types: frozenset[str]
    project_keys: frozenset[str] | None
    count_subtasks: bool


@dataclass(frozen=True)
class TeamConfig:
    version: int
    catalog_version: int
    team_id: str
    team_name: str
    members: tuple[Member, ...]
    alumni: tuple[Member, ...]
    calendar: Calendar
    period_id: str
    period_start: date
    period_end: date
    deployment: str
    sprint_id: str | None
    auth_env: str | None
    jira_base_url: str | None
    story_points_field: str | None
    uses_due_date: bool
    status_map: tuple[StatusRule, ...]
    taxonomy: Taxonomy
    scope: Scope
    min_stay_seconds: int
    high_priorities: tuple[str, ...]
    max_age_days: int
    unknown_warn_pct: float
    raw_calendar: dict
    raw_workflow: dict
    raw_taxonomy: dict
    raw_scope: dict

    def status(self, name: str) -> StatusRule | None:
        for rule in self.status_map:
            if rule.status == name:
                return rule
        return None

    def assignee_key(self, member: Member) -> str | None:
        if self.deployment == "cloud":
            return member.jira_account_id
        return member.jira_username
