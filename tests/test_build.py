"""Сборка: write-once, правки не переписываются, чужой хеш останавливает build."""

import importlib
import json
from pathlib import Path

from dashboard.config.hash import rule_hash
from dashboard.config.load import load_team
from dashboard.orchestrator.build import BuildRequest, build

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "schema" / "examples"


def _request(tmp_path: Path, **kwargs) -> BuildRequest:
    team = tmp_path / "team.yaml"
    bundle = tmp_path / "canonical.json"
    edits = tmp_path / "edits.json"
    team.write_text((EXAMPLE / "team.example.yaml").read_text())
    bundle.write_text((EXAMPLE / "canonical.example.json").read_text())
    edits.write_text((EXAMPLE / "edits.example.json").read_text())
    return BuildRequest(
        team_path=team,
        bundle_path=bundle,
        out_dir=tmp_path / "out",
        edits_path=edits,
        **kwargs,
    )


def test_build_writes_snapshot_and_keeps_edits(tmp_path: Path):
    request = _request(tmp_path)
    before = request.edits_path.read_bytes()
    result = build(request)
    assert result.code == 0
    assert result.path.read_bytes()
    assert request.edits_path.read_bytes() == before
    document = json.loads(result.path.read_text())
    row = next(item for item in document["period"]["metrics"] if item["id"] == "projectList")
    epic = next(item for item in row["detail"]["rows"] if item["key"] == "CARD-10")
    assert epic["release"] == "2026-Q3"
    assert epic["note"] == "Ждём дизайн пустого состояния"
    cycle = next(item for item in document["sprint"]["metrics"] if item["id"] == "cycleTime")
    assert "900" in cycle["explain"]


def test_second_build_does_not_open_the_file_for_write(tmp_path: Path, monkeypatch):
    request = _request(tmp_path)
    first = build(request)
    payload = first.path.read_bytes()

    def boom(*_args, **_kwargs):
        raise AssertionError("повторный build открыл слепок на запись")

    module = importlib.import_module("dashboard.orchestrator.build")
    monkeypatch.setattr(module, "write_new", boom)
    second = build(request)
    assert second.code == 0
    assert first.path.read_bytes() == payload


def test_changed_inputs_do_not_replace_bytes(tmp_path: Path):
    request = _request(tmp_path)
    first = build(request)
    payload = first.path.read_bytes()
    raw = json.loads(request.bundle_path.read_text())
    raw["issues"][0]["summary"] = "Другое название"
    request.bundle_path.write_text(json.dumps(raw))
    second = build(request)
    assert second.code == 4
    assert first.path.read_bytes() == payload


def test_status_map_change_stops_without_acceptance(tmp_path: Path):
    request = _request(tmp_path, manifest_path=tmp_path / "manifest.json")
    request.manifest_path.write_text((EXAMPLE / "manifest.example.json").read_text())
    edits_before = request.edits_path.read_bytes()
    result = build(request)
    assert result.code == 3
    assert not (tmp_path / "out").exists()
    assert request.edits_path.read_bytes() == edits_before


def test_accept_recompute_clears_sealed_timings(tmp_path: Path):
    request = _request(tmp_path, manifest_path=tmp_path / "manifest.json", accept_recompute=True)
    request.manifest_path.write_text((EXAMPLE / "manifest.example.json").read_text())
    result = build(request)
    assert result.code == 0
    manifest = json.loads(request.manifest_path.read_text())
    config = load_team(request.team_path)
    assert manifest["ruleHash"] == rule_hash(config)
    assert manifest["timings"] == []


def test_import_boundary():
    root = Path(__file__).resolve().parents[1] / "src" / "dashboard"
    metrics = "\n".join(path.read_text() for path in (root / "metrics").glob("*.py"))
    config = "\n".join(path.read_text() for path in (root / "config").glob("*.py"))
    assert "snapshotstore" not in metrics
    assert "orchestrator" not in metrics
    assert "dashboard.metrics" not in config
    assert "open(" not in metrics
