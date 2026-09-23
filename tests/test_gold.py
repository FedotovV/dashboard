"""Золотые пары. Ожидаемые числа лежат в fixtures/m1 и написаны по каталогу."""

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from dashboard.config.hash import digest
from dashboard.orchestrator.build import BuildRequest, build

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "m1"
SCHEMA = json.loads((ROOT / "schema" / "snapshot.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

FORMULA_CASES = [
    "due-midnight",
    "cycle-reopen",
    "parallel-day",
    "classify",
    "scope-days",
    "no-points",
    "points-moved",
    "pace-zero",
    "write-once",
    "edits-intact",
]


def _expected(case: str) -> dict:
    return json.loads((FIXTURES / case / "expected.snapshot.json").read_text())


def _request(case: str, tmp_path: Path) -> BuildRequest:
    source = FIXTURES / case
    team = tmp_path / "team.yaml"
    bundle = tmp_path / "canonical.json"
    shutil.copy(source / "team.yaml", team)
    shutil.copy(source / "canonical.json", bundle)
    edits = None
    if (source / "edits.json").exists():
        edits = tmp_path / "edits.json"
        shutil.copy(source / "edits.json", edits)
    out = tmp_path / "out"
    history = source / "history"
    if history.exists():
        shutil.copytree(history, out / "card")
    return BuildRequest(team_path=team, bundle_path=bundle, out_dir=out, edits_path=edits)


def _assert_locked(built: dict, expected: dict) -> None:
    for section in ("sprint", "period"):
        if section not in expected:
            continue
        actual = {item["id"]: item for item in built[section]["metrics"]}
        for metric in expected[section]["metrics"]:
            got = actual[metric["id"]]
            for key in ("version", "unit", "value", "population", "excluded", "warnings", "params", "explain"):
                if key in metric:
                    assert got[key] == metric[key], (section, metric["id"], key)
            if "detail" in metric:
                for key, value in metric["detail"].items():
                    assert got["detail"][key] == value, (metric["id"], key)
    if "issues" in expected["sprint"]:
        rows = {item["key"]: item for item in built["sprint"]["issues"]}
        for issue in expected["sprint"]["issues"]:
            for key, value in issue.items():
                assert rows[issue["key"]][key] == value, (issue["key"], key)
    if "trend" in expected["sprint"]:
        assert built["sprint"]["trend"] == expected["sprint"]["trend"]
    for key, value in expected["coverage"].items():
        assert built["coverage"][key] == value, key


@pytest.mark.parametrize("case", [*FORMULA_CASES, "rules-changed"])
def test_expected_snapshot_matches_schema(case: str):
    errors = sorted(VALIDATOR.iter_errors(_expected(case)), key=lambda item: list(item.path))
    assert errors == []


@pytest.mark.parametrize("case", FORMULA_CASES)
def test_build_matches_hand_written_numbers(case: str, tmp_path: Path):
    request = _request(case, tmp_path)
    edits_before = request.edits_path.read_bytes() if request.edits_path else None
    result = build(request)
    assert result.code == 0, result.message
    built = json.loads(result.path.read_text())
    errors = list(VALIDATOR.iter_errors(built))
    assert errors == [], errors[0].message if errors else ""
    raw = json.loads(request.bundle_path.read_text())
    assert built["inputHashes"]["bundle"] == digest(raw)
    _assert_locked(built, _expected(case))
    if edits_before is not None:
        assert request.edits_path.read_bytes() == edits_before
    if case == "scope-days":
        dates = [point["date"] for point in built["sprint"]["trend"]["sparkline"]]
        assert "2026-09-11" not in dates
    if case == "write-once":
        payload = result.path.read_bytes()
        second = build(request)
        assert second.code == 0
        assert result.path.read_bytes() == payload


def test_rules_changed_does_not_write_a_snapshot(tmp_path: Path):
    source = FIXTURES / "rules-changed"
    team = tmp_path / "team.yaml"
    bundle = tmp_path / "canonical.json"
    manifest = tmp_path / "manifest.json"
    shutil.copy(source / "team.yaml", team)
    shutil.copy(source / "canonical.json", bundle)
    shutil.copy(source / "manifest.json", manifest)
    before = manifest.read_bytes()
    result = build(
        BuildRequest(
            team_path=team,
            bundle_path=bundle,
            out_dir=tmp_path / "out",
            manifest_path=manifest,
        )
    )
    assert result.code == 3
    assert not (tmp_path / "out").exists()
    assert manifest.read_bytes() == before
