"""collect: sources.mode → canonical JSON. Формулы не вызывает."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from dashboard.config.load import ConfigError, load_team
from dashboard.connectors import CollectError, collect_bundle

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema" / "canonical.schema.json"


@dataclass
class CollectRequest:
    team_path: Path
    source: Path
    bundle_path: Path
    transport: object | None = None
    now: datetime | None = None
    environ: dict | None = None


@dataclass
class CollectResult:
    code: int
    message: str
    path: Path | None = None
    bundle: dict | None = None


def collect(request: CollectRequest) -> CollectResult:
    try:
        load_team(request.team_path)
        raw = yaml.safe_load(request.team_path.read_text())
        sources = raw.get("sources") or {}
        mode = sources.get("mode") or "fixture"
        bundle = collect_bundle(
            mode,
            request.source,
            sources,
            transport=request.transport,
            now=request.now,
            environ=request.environ,
        )
        _validate(bundle)
    except (ConfigError, CollectError, OSError, yaml.YAMLError, ValueError) as exc:
        return CollectResult(2, str(exc))
    request.bundle_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    request.bundle_path.write_text(payload)
    return CollectResult(0, "bundle записан", request.bundle_path, bundle)


def _validate(instance: dict) -> None:
    schema = json.loads(SCHEMA.read_text())
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"canonical.schema.json: {list(errors[0].path)}: {errors[0].message}")
