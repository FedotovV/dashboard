"""Инварианты team.yaml. Их же проверяет scripts/check_contracts.py."""

from __future__ import annotations


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
        break_start = calendar.get("breakStart")
        if break_start and break_minutes:
            break_at = hhmm_minutes(break_start)
            if break_at < start or break_at + break_minutes > end:
                problems.append(f"{label}: перерыв выходит за [workStart, workEnd)")
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
        if str(link_type).lower() in {"blocks", "block", "блокировка"}:
            problems.append(f"{label}: {link_type} не иерархия и не может быть ребром таксономии")
    return problems
