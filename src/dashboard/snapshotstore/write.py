"""Запись слепка. Повторный путь на запись не открывается."""

from __future__ import annotations

import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_SCHEMA = ROOT / "schema" / "snapshot.schema.json"


class SnapshotError(ValueError):
    """Документ не проходит схему снимка."""


def document_bytes(document: dict) -> bytes:
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def validate_snapshot(document: dict) -> None:
    schema = json.loads(SNAPSHOT_SCHEMA.read_text())
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document),
        key=lambda item: list(item.path),
    )
    if errors:
        raise SnapshotError(f"{list(errors[0].path)}: {errors[0].message}")


def write_new(document: dict, dest: Path) -> None:
    if dest.exists():
        raise FileExistsError(dest)
    validate_snapshot(document)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(document_bytes(document))
