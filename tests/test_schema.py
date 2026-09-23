"""Срез 0. Схема снимка и положение перерыва, без движка."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from scripts.check_contracts import (
    check_team_invariants,
    load_json,
    load_yaml,
    validator,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema"
EXAMPLES = SCHEMA / "examples"


def test_contracts_script_ok():
    from scripts.check_contracts import main

    assert main() == 0


def test_snapshot_example_keeps_new_fields():
    schema = load_json(SCHEMA / "snapshot.schema.json")
    example = load_json(EXAMPLES / "snapshot.example.json")
    assert example["inputHashes"]["bundle"]
    assert example["sprint"]["issues"][0]["dueDate"] == "2026-09-12"
    assert example["sprint"]["trend"]["sparkline"] == []
    errors = list(Draft202012Validator(schema).iter_errors(example))
    assert errors == []


def test_snapshot_without_bundle_hash_fails():
    schema = load_json(SCHEMA / "snapshot.schema.json")
    example = load_json(EXAMPLES / "snapshot.example.json")
    del example["inputHashes"]["bundle"]
    errors = list(validator(schema).iter_errors(example))
    assert errors


def test_trend_previous_shape():
    schema = load_json(SCHEMA / "snapshot.schema.json")
    example = load_json(EXAMPLES / "snapshot.example.json")
    example["sprint"]["trend"] = {
        "previous": {
            "snapshotId": "payments-card-2026-08-28",
            "sprintId": "s-prev",
            "byRole": {
                "active": 0,
                "wait": 0,
                "hold": 0,
                "queue": 0,
                "done": 4,
                "canceled": 0,
                "total": 4,
            },
        },
        "sparkline": [{"date": "2026-09-08", "done": 1}],
    }
    assert list(validator(schema).iter_errors(example)) == []


def test_break_start_inside_window_passes():
    team = load_yaml(EXAMPLES / "team.no-points.yaml")
    team["calendar"]["breakStart"] = "13:00"
    assert check_team_invariants(team, "break") == []


def test_break_start_outside_window_fails():
    team = load_yaml(EXAMPLES / "team.example.yaml")
    team["calendar"]["breakMinutes"] = 60
    team["calendar"]["hoursPerDay"] = 7
    team["calendar"]["breakStart"] = "17:30"
    problems = check_team_invariants(team, "break")
    assert any("перерыв" in item for item in problems)


def test_existing_examples_have_no_break_start():
    for name in ("team.example.yaml", "team.no-points.yaml"):
        data = load_yaml(EXAMPLES / name)
        assert "breakStart" not in data["calendar"]
        schema = load_json(SCHEMA / "team.schema.json")
        assert list(validator(schema).iter_errors(data)) == []


def test_closed_before_due_accepts_bool_and_null():
    schema = load_json(SCHEMA / "snapshot.schema.json")
    example = load_json(EXAMPLES / "snapshot.example.json")
    example["sprint"]["issues"][0]["closedBeforeDue"] = True
    assert list(validator(schema).iter_errors(example)) == []
    example["sprint"]["issues"][0]["closedBeforeDue"] = "yes"
    with_error = list(validator(schema).iter_errors(example))
    assert with_error
    assert any(isinstance(item, ValidationError) for item in with_error)


def test_schema_files_are_json():
    for path in SCHEMA.glob("*.json"):
        json.loads(path.read_text())
        copy.deepcopy(json.loads(path.read_text()))
