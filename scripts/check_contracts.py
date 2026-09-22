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


def hhmm_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def check_team_invariants(data: dict, label: str) -> list[str]:
    problems: list[str] = []
    calendar = data["calendar"]
    start = hhmm_minutes(calendar["workStart"])
    end = hhmm_minutes(calendar["workEnd"])
    break_minutes = calendar.get("breakMinutes", 0)
    if end <= start:
        problems.append(f"{label}: workEnd должен быть позже workStart")
    else:
        hours = (end - start - break_minutes) / 60
        if abs(hours - calendar["hoursPerDay"]) > 1e-9:
            problems.append(
                f"{label}: окно {hours} ч минус перерыв не равно hoursPerDay {calendar['hoursPerDay']}"
            )
    if data["period"]["end"] < data["period"]["start"]:
        problems.append(f"{label}: period.end раньше period.start")
    people = [*data["team"]["members"], *data["team"].get("alumni", [])]
    ids = [person["id"] for person in people]
    if len(ids) != len(set(ids)):
        problems.append(f"{label}: id людей не уникальны, members и alumni пересекаются")
    holidays = set(calendar.get("holidays") or [])
    extra = set(calendar.get("extraWorkdays") or [])
    if holidays & extra:
        problems.append(f"{label}: дата одновременно праздник и рабочий день")
    project = set(data["taxonomy"]["epics"]["project"])
    tech = set(data["taxonomy"]["epics"]["tech"])
    if project & tech:
        problems.append(f"{label}: эпик одновременно в project и tech")
    statuses = [row["status"] for row in data["workflow"]["statusMap"]]
    if len(statuses) != len(set(statuses)):
        problems.append(f"{label}: статус повторяется в statusMap")
    for row in data["workflow"]["statusMap"]:
        role, category = row["role"], row["category"]
        if role == "terminal" and category != "done":
            problems.append(f"{label}: terminal-статус {row['status']} должен иметь category done")
        if role == "queue" and category != "todo":
            problems.append(f"{label}: queue-статус {row['status']} должен иметь category todo")
        if role in {"active", "wait", "hold"} and category != "indeterminate":
            problems.append(
                f"{label}: статус {row['status']} с ролью {role} должен иметь category indeterminate"
            )
    for link_type in data["taxonomy"].get("linkTypes") or ["Child-Issue"]:
        if link_type.lower() in {"blocks", "block", "блокировка"}:
            problems.append(f"{label}: {link_type} не иерархия и не может быть ребром таксономии")
    return problems


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
