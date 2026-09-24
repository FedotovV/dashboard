"""Порядок build. Единственное место, где модули встречаются."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from dashboard.config.hash import digest, input_hashes, rule_hash
from dashboard.config.load import ConfigError, load_team
from dashboard.edits.apply import apply_edits, edits_from_dict
from dashboard.metrics.engine import History, HistoryPoint, compute
from dashboard.metrics.parse import bundle_from_dict
from dashboard.metrics.time import local_date
from dashboard.snapshotstore.write import SnapshotError, document_bytes, validate_snapshot, write_new

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema"


@dataclass
class BuildRequest:
    team_path: Path
    bundle_path: Path
    out_dir: Path
    edits_path: Path | None = None
    manifest_path: Path | None = None
    accept_recompute: bool = False


@dataclass
class BuildResult:
    code: int
    message: str
    path: Path | None = None


def build(request: BuildRequest) -> BuildResult:
    try:
        config = load_team(request.team_path)
    except ConfigError as exc:
        return BuildResult(2, str(exc))
    try:
        manifest = _read_manifest(request.manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return BuildResult(2, str(exc))
    if manifest is not None and manifest["ruleHash"] != rule_hash(config) and not request.accept_recompute:
        return BuildResult(3, "хеш правил разошёлся с manifest, build остановлен")
    try:
        bundle_raw = json.loads(request.bundle_path.read_text())
        _validate(SCHEMA / "canonical.schema.json", bundle_raw)
        bundle = bundle_from_dict(bundle_raw)
        edits_bytes, edits = _read_edits(request.edits_path, config.team_id)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return BuildResult(2, str(exc))
    try:
        computed = compute(
            bundle,
            config,
            as_of=bundle.as_of,
            history=_history(request.out_dir, config.team_id, bundle, config.sprint_id),
        )
    except ValueError as exc:
        return BuildResult(2, str(exc))
    apply_edits(computed.period_metrics, edits, config.team_id)
    document = _document(computed, config, digest(bundle_raw))
    try:
        validate_snapshot(document)
    except SnapshotError as exc:
        return BuildResult(2, str(exc))
    dest = request.out_dir / config.team_id / f"{local_date(bundle.as_of, config.calendar.timezone).isoformat()}.json"
    payload = document_bytes(document)
    if dest.exists():
        if dest.read_bytes() != payload:
            _assert_edits(request.edits_path, edits_bytes)
            return BuildResult(4, "слепок дня уже есть и отличается, байты не менялись", dest)
        code = BuildResult(0, "слепок дня уже записан", dest)
    else:
        write_new(document, dest)
        code = BuildResult(0, "слепок записан", dest)
    _assert_edits(request.edits_path, edits_bytes)
    if request.accept_recompute and request.manifest_path is not None:
        _write_manifest(request.manifest_path, config)
    return code


def _read_manifest(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    data = json.loads(path.read_text())
    _validate(SCHEMA / "manifest.schema.json", data)
    return data


def _read_edits(path: Path | None, team_id: str):
    if path is None or not path.exists():
        empty = {
            "teamId": team_id,
            "revision": 1,
            "projectReleases": [],
            "projectNotes": [],
        }
        return None, edits_from_dict(empty)
    raw = path.read_bytes()
    data = json.loads(raw)
    _validate(SCHEMA / "edits.schema.json", data)
    return raw, edits_from_dict(data)


def _assert_edits(path: Path | None, original: bytes | None) -> None:
    if path is None or original is None or not path.exists():
        return
    if path.read_bytes() != original:
        raise RuntimeError("build изменил edits.json")


def _history(out_dir: Path, team_id: str, bundle, sprint_id: str | None) -> History:
    directory = out_dir / team_id
    points: list[HistoryPoint] = []
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            try:
                day = date.fromisoformat(path.stem)
                data = json.loads(path.read_text())
            except (ValueError, json.JSONDecodeError):
                continue
            sprint = data.get("sprint") or {}
            flow = next(
                (item for item in sprint.get("metrics") or [] if item.get("id") == "sprintFlow"),
                None,
            )
            by_role = ((flow or {}).get("detail") or {}).get("byRole")
            if not by_role or "id" not in sprint:
                continue
            points.append(
                HistoryPoint(
                    as_of_date=day,
                    sprint_id=sprint["id"],
                    snapshot_id=data.get("snapshotId") or path.stem,
                    by_role=by_role,
                )
            )
    previous = None
    if sprint_id:
        current = next((item for item in bundle.sprints if item.id == sprint_id), None)
        if current is not None:
            earlier = [item for item in bundle.sprints if item.end < current.start]
            if earlier:
                prev = max(earlier, key=lambda item: item.end)
                candidates = [point for point in points if point.sprint_id == prev.id]
                if candidates:
                    previous = max(candidates, key=lambda point: point.as_of_date)
    return History(points=tuple(points), previous=previous)


def _document(computed, config, bundle_hash: str) -> dict:
    hashes = input_hashes(config)
    hashes["bundle"] = bundle_hash
    metrics = [*computed.sprint_metrics, *computed.period_metrics]
    return {
        "snapshotId": f"{config.team_id}-{local_date(computed.as_of, config.calendar.timezone).isoformat()}",
        "teamId": config.team_id,
        "asOf": _utc(computed.as_of),
        "timezone": config.calendar.timezone,
        "catalogVersion": config.catalog_version,
        "metricVersions": {metric.id: metric.version for metric in metrics},
        "inputHashes": hashes,
        "coverage": computed.coverage,
        "jiraBaseUrl": config.jira_base_url,
        "sprint": {
            "id": computed.sprint_id,
            "start": computed.sprint_start.isoformat(),
            "end": computed.sprint_end.isoformat(),
            "metrics": [metric.to_json() for metric in computed.sprint_metrics],
            "trend": computed.trend,
            "issues": computed.issues,
        },
        "period": {
            "id": computed.period_id,
            "start": computed.period_start.isoformat(),
            "end": computed.period_end.isoformat(),
            "metrics": [metric.to_json() for metric in computed.period_metrics],
        },
    }


def _utc(instant: datetime) -> str:
    return instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_manifest(path: Path, config) -> None:
    payload = {
        "teamId": config.team_id,
        "ruleHash": rule_hash(config),
        "catalogVersion": config.catalog_version,
        "timings": [],
    }
    _validate(SCHEMA / "manifest.schema.json", payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _validate(schema_path: Path, instance: dict) -> None:
    schema = json.loads(schema_path.read_text())
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"{schema_path.name}: {list(errors[0].path)}: {errors[0].message}")
