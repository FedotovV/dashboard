"""Файл правок. Чисел метрик в нём нет: схема отсекает лишние поля."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from dashboard.edits.apply import Edits, edits_from_dict

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema" / "edits.schema.json"
TEXT_LIMIT = 4000


class EditsError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def read_document(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditsError(422, "файл правок не читается") from exc
    if not isinstance(data, dict):
        raise EditsError(422, "файл правок не читается")
    _validate(data)
    return data


def read_edits(path: Path | None) -> Edits | None:
    if path is None:
        return None
    data = read_document(path)
    if data is None:
        return None
    return edits_from_dict(data)


def empty_document(team_id: str) -> dict:
    return {
        "teamId": team_id,
        "revision": 1,
        "projectReleases": [],
        "projectNotes": [],
    }


def store_document(path: Path, document: dict, team_id: str) -> dict:
    if not isinstance(document, dict):
        raise EditsError(422, "тело не объект")
    _validate(document)
    if document["teamId"] != team_id:
        raise EditsError(422, "teamId не совпадает с командой сервера")
    current = read_document(path)
    expected = 1 if current is None else current["revision"] + 1
    if document["revision"] != expected:
        raise EditsError(409, "revision должна быть на 1 больше текущей")
    _write(path, document)
    return document


def merge_form(path: Path, team_id: str, fields: dict, now: datetime) -> dict:
    epic = str(fields.get("epicId") or "").strip()
    release = str(fields.get("release") or "").strip()
    text = str(fields.get("text") or "").strip()
    author = str(fields.get("author") or "").strip()
    if not epic:
        raise EditsError(422, "нужен epicId")
    if not release and not text:
        raise EditsError(422, "нужен релиз или заметка")
    if text and not author:
        raise EditsError(422, "нужен author")
    if len(text) > TEXT_LIMIT or len(release) > TEXT_LIMIT or len(author) > 200 or len(epic) > 200:
        raise EditsError(422, "поле слишком длинное")
    current = read_document(path)
    if current is not None and current["teamId"] != team_id:
        raise EditsError(422, "teamId не совпадает с командой сервера")
    base = current or {
        "teamId": team_id,
        "revision": 0,
        "projectReleases": [],
        "projectNotes": [],
    }
    releases = [dict(item) for item in base["projectReleases"] if item["epicId"] != epic]
    if release:
        releases.append({"epicId": epic, "release": release})
    notes = [dict(item) for item in base["projectNotes"]]
    if text:
        notes.append(
            {
                "epicId": epic,
                "text": text,
                "author": author,
                "at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    document = {
        "teamId": team_id,
        "revision": base["revision"] + 1,
        "projectReleases": releases,
        "projectNotes": notes,
    }
    _validate(document)
    _write(path, document)
    return document


def _validate(document: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document),
        key=lambda item: list(item.path),
    )
    if errors:
        raise EditsError(422, f"edits.schema.json: {list(errors[0].path)}: {errors[0].message}")


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
