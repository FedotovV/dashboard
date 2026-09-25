"""Проверка контрактов дашборда. Зависимости: PyYAML, jsonschema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema"
EXAMPLES = SCHEMA / "examples"
FORMATS = FormatChecker()
sys.path.insert(0, str(ROOT / "src"))

from dashboard.config.invariants import check_team_invariants  # noqa: E402


def load_json(path: Path):
    return json.loads(path.read_text())


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def validator(schema: dict) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMATS)


def errors(v: Draft202012Validator, instance) -> list[str]:
    found = sorted(v.iter_errors(instance), key=lambda e: list(e.path))
    return [f"{list(e.path)}: {e.message}" for e in found]


def main() -> int:
    problems: list[str] = []
    team_schema = load_json(SCHEMA / "team.schema.json")
    team_validator = validator(team_schema)
    teams = {
        "team.example.yaml": load_yaml(EXAMPLES / "team.example.yaml"),
        "team.no-points.yaml": load_yaml(EXAMPLES / "team.no-points.yaml"),
    }
    for label, data in teams.items():
        problems.extend(f"{label}: {item}" for item in errors(team_validator, data))
        problems.extend(check_team_invariants(data, label))

    cloud = json.loads(json.dumps(teams["team.no-points.yaml"]))
    del cloud["team"]["members"][0]["jiraAccountId"]
    if not errors(team_validator, cloud):
        problems.append("cloud без jiraAccountId обязан не проходить схему")

    pairs = [
        ("canonical.schema.json", "canonical.example.json"),
        ("snapshot.schema.json", "snapshot.example.json"),
        ("edits.schema.json", "edits.example.json"),
        ("manifest.schema.json", "manifest.example.json"),
    ]
    for schema_name, example_name in pairs:
        schema = load_json(SCHEMA / schema_name)
        example = load_json(EXAMPLES / example_name)
        found = errors(validator(schema), example)
        problems.extend(f"{example_name}: {item}" for item in found)

    if problems:
        print("\n".join(problems))
        return 1
    print("contracts ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
