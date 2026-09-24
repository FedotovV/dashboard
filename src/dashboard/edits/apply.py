"""Подстановка релиза и заметки. Файл правок модуль не открывает."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dashboard.metrics.results import Metric


@dataclass(frozen=True)
class Release:
    epic_id: str
    release: str


@dataclass(frozen=True)
class Note:
    epic_id: str
    text: str
    author: str
    at: datetime


@dataclass(frozen=True)
class Edits:
    team_id: str
    revision: int
    releases: tuple[Release, ...]
    notes: tuple[Note, ...]


def edits_from_dict(data: dict) -> Edits:
    return Edits(
        team_id=data["teamId"],
        revision=data["revision"],
        releases=tuple(
            Release(epic_id=item["epicId"], release=item["release"]) for item in data["projectReleases"]
        ),
        notes=tuple(
            Note(
                epic_id=item["epicId"],
                text=item["text"],
                author=item["author"],
                at=datetime.fromisoformat(item["at"].replace("Z", "+00:00")),
            )
            for item in data["projectNotes"]
        ),
    )


def annotate_rows(rows: list[dict], edits: Edits, team_id: str, *, replace: bool = False) -> list[str]:
    """Подставляет релиз и заметку в строки эпиков. Чужой id остаётся предупреждением."""
    if edits.team_id != team_id:
        return ["edits-team-mismatch"]
    if replace:
        for row in rows:
            row["release"] = None
            row["note"] = None
    indexed = {row["key"]: row for row in rows}
    warnings: list[str] = []
    for release in edits.releases:
        row = indexed.get(release.epic_id)
        if row is None:
            warnings.append(f"unknown-epic:{release.epic_id}")
            continue
        row["release"] = release.release
    for note in sorted(edits.notes, key=lambda item: item.at):
        row = indexed.get(note.epic_id)
        if row is None:
            warnings.append(f"unknown-epic:{note.epic_id}")
            continue
        row["note"] = note.text
    return warnings


def apply_edits(metrics: list[Metric], edits: Edits, team_id: str) -> None:
    metric = next((item for item in metrics if item.id == "projectList"), None)
    if metric is None or metric.detail is None:
        return
    metric.warnings.extend(annotate_rows(metric.detail["rows"], edits, team_id))
