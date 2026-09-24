"""Документ маршрута из файла слепка. compute не вызывается."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

from dashboard.edits.apply import Edits, annotate_rows
from dashboard.snapshotstore.write import SnapshotError, validate_snapshot

SCREEN_METRICS = (
    "cycleTime",
    "waitTime",
    "sprintFlow",
    "scopeChange",
    "completionVsCommitted",
    "hygiene",
    "blockers",
    "personLoad",
    "burndown",
)
PERIOD_METRICS = (
    "classification",
    "statusHours",
    "projectList",
)


class RouteError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def resolve_snapshot(root: Path, team_id: str, day: str | None = None) -> Path:
    directory = root / team_id
    if day is not None:
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise RouteError(404, "слепка нет") from exc
        path = directory / f"{day}.json"
        if not path.is_file():
            raise RouteError(404, "слепка нет")
        return path
    if not directory.is_dir():
        raise RouteError(404, "слепка нет")
    dated = []
    for path in directory.glob("*.json"):
        try:
            date.fromisoformat(path.stem)
        except ValueError:
            continue
        dated.append(path)
    if not dated:
        raise RouteError(404, "слепка нет")
    return sorted(dated)[-1]


def load_snapshot(path: Path) -> dict:
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RouteError(422, "слепок не читается") from exc
    if not isinstance(document, dict):
        raise RouteError(422, "слепок не читается")
    try:
        validate_snapshot(document)
    except SnapshotError as exc:
        raise RouteError(422, str(exc)) from exc
    return document


def sprint_view(document: dict) -> dict:
    return {
        "asOf": document["asOf"],
        "timezone": document["timezone"],
        "teamId": document["teamId"],
        "coverage": document["coverage"],
        "jiraBaseUrl": document.get("jiraBaseUrl"),
        "sprint": document["sprint"],
    }


def team_view(document: dict, edits: Edits | None = None) -> dict:
    period = copy.deepcopy(document.get("period") or {"id": "", "start": "", "end": "", "metrics": []})
    if edits is not None:
        _overlay_edits(period, edits, document["teamId"])
    sprint = document.get("sprint") or {}
    return {
        "asOf": document["asOf"],
        "timezone": document["timezone"],
        "teamId": document["teamId"],
        "coverage": document["coverage"],
        "jiraBaseUrl": document.get("jiraBaseUrl"),
        "period": period,
        "trend": sprint.get("trend"),
        "completion": _metric(sprint, "completionVsCommitted"),
        "people": _metric(sprint, "personLoad"),
        "issues": sprint.get("issues") or [],
    }


def metric_brief(document: dict, metric_id: str) -> dict:
    if metric_id not in SCREEN_METRICS and metric_id not in PERIOD_METRICS:
        raise RouteError(404, "метрики нет на этом экране")
    for section in ("sprint", "period"):
        for metric in (document.get(section) or {}).get("metrics") or []:
            if metric.get("id") == metric_id:
                return {
                    "id": metric_id,
                    "version": metric.get("version"),
                    "explain": metric.get("explain") or "",
                    "params": metric.get("params") or {},
                }
    raise RouteError(404, "метрики нет в слепке")


def _metric(sprint: dict, metric_id: str) -> dict | None:
    for metric in sprint.get("metrics") or []:
        if metric.get("id") == metric_id:
            return metric
    return None


def _overlay_edits(period: dict, edits: Edits, team_id: str) -> None:
    for metric in period.get("metrics") or []:
        if metric.get("id") != "projectList":
            continue
        detail = metric.setdefault("detail", {})
        rows = detail.setdefault("rows", [])
        kept = [
            item
            for item in metric.get("warnings") or []
            if item != "edits-team-mismatch" and not str(item).startswith("unknown-epic:")
        ]
        kept.extend(annotate_rows(rows, edits, team_id, replace=True))
        metric["warnings"] = kept
