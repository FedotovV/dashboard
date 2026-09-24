"""Документ маршрута из файла слепка. compute не вызывается."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

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


def metric_brief(document: dict, metric_id: str) -> dict:
    if metric_id not in SCREEN_METRICS:
        raise RouteError(404, "метрики нет на этом экране")
    for metric in document["sprint"].get("metrics") or []:
        if metric.get("id") == metric_id:
            return {
                "id": metric_id,
                "version": metric.get("version"),
                "explain": metric.get("explain") or "",
                "params": metric.get("params") or {},
            }
    raise RouteError(404, "метрики нет в слепке")
