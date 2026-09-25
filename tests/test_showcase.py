"""Команда «Платёжная карта»: прошлый спринт закрыт, текущий на предпоследнем дне."""

from pathlib import Path

from dashboard.api.page import render_sprint
from dashboard.api.period import render_period
from dashboard.api.preview import refresh
from dashboard.api.read import load_snapshot, sprint_view, team_view

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "fixtures" / "ui" / "showcase.json"


def test_showcase_fills_different_card_states(tmp_path: Path):
    result = refresh(SHOWCASE, tmp_path)
    assert result.code == 0, result.message
    document = load_snapshot(result.path)
    sprint = document["sprint"]
    metrics = {item["id"]: item for item in sprint["metrics"]}
    period = {item["id"]: item for item in document["period"]["metrics"]}

    assert document["teamId"] == "paycard"
    assert sprint["id"] == "Спринт 24"
    assert sprint["end"] == "2026-09-18"
    previous = sprint["trend"]["previous"]
    assert previous["sprintId"] == "Спринт 23"
    assert previous["byRole"]["done"] == 14
    assert previous["byRole"]["canceled"] == 1
    assert previous["byRole"]["total"] == 15
    assert [point["date"] for point in sprint["trend"]["sparkline"]] == [
        "2026-09-08",
        "2026-09-10",
        "2026-09-15",
        "2026-09-17",
    ]

    scope = metrics["scopeChange"]["detail"]
    assert scope["addedKeys"] == ["PAY-17", "PAY-18"]
    assert scope["removedKeys"] == ["PAY-19"]
    assert scope["committed"] > 0
    completion = metrics["completionVsCommitted"]
    assert completion["detail"]["done"] < completion["detail"]["committed"]

    assert [item["issueKey"] for item in metrics["blockers"]["detail"]["items"]] == [
        "PAY-7",
        "PAY-8",
        "PAY-9",
    ]
    assert {item["reason"] for item in metrics["hygiene"]["detail"]["items"]} == {
        "high-priority-queue",
        "too-old",
        "no-story-points",
        "no-due-date",
        "no-assignee",
    }
    excluded = {item["reason"] for item in metrics["cycleTime"]["excluded"]}
    assert excluded == {"shorter-than-min-stay", "no-timing"}
    assert metrics["sprintFlow"]["detail"]["byRole"]["hold"] == 1
    assert metrics["sprintFlow"]["detail"]["byRole"]["canceled"] == 1
    assert metrics["sprintFlow"]["detail"]["byRole"]["wait"] > 0

    points = metrics["burndown"]["detail"]["points"]
    assert metrics["burndown"]["value"] is not None
    assert points[-1]["actual"] > points[-1]["ideal"]
    assert document["coverage"]["storyPoints"] == "full"
    assert document["coverage"]["timing"] == "partial"
    assert document["coverage"]["membership"] == "complete"
    assert document["coverage"]["unknownPct"] > 15

    people = {row["personId"]: row for row in metrics["personLoad"]["detail"]["rows"]}
    assert people["novikova"]["openKeys"] == []
    assert people["novikova"]["total"] == 0
    assert people["pavlova"]["openKeys"] == []
    assert people["pavlova"]["done"] > 0
    assert people["morozov"]["pointsMissing"] == 1
    assert people["smirnov"]["paused"] == 1
    assert people["smirnov"]["canceled"] == 1

    paths = {item["issueKey"]: item["reason"] for item in period["classification"]["detail"]["paths"]}
    assert "unknown-above-threshold" in period["classification"]["warnings"]
    assert paths["PAY-1"] == "head"
    assert paths["PAY-14"] == "rule"
    assert paths["PAY-6"] == "label"
    assert paths["PAY-21"] == "label"
    hours = period["statusHours"]["detail"]
    assert hours["inheritedSeconds"] > 0
    assert hours["ownSeconds"] > 0
    outside = [row for row in hours["days"] if row["outside"]]
    assert outside and outside[0]["personId"] == "vneshtat"
    epics = {row["key"]: row for row in period["projectList"]["detail"]["rows"]}
    assert epics["PAY-100"]["release"] == "2026.09"
    assert epics["PAY-100"]["note"]
    assert epics["PAY-200"]["note"] is None
    assert "unknown-epic:PAY-999" in period["projectList"]["warnings"]

    page = render_sprint(sprint_view(document))
    assert "Команда paycard" in page
    assert "Прошлый спринт" in page
    assert "нет открытых" in page
    assert "раньше срока" in page
    assert 'data-attention="true"' in page
    assert 'href="https://jira.example.com/browse/PAY-7"' in page
    assert "Тайминги: coverage.timing = partial" in page
    period_page = render_period(team_view(document))
    assert "Не разобрано" in period_page
    assert "Чужой эпик PAY-999" in period_page
    assert "Релиз в пятницу" in period_page
    assert "вне состава" in period_page or "vneshtat" in period_page
