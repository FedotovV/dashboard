"""Стенд UI собирается из редактируемого JSON и повторяет актуальное состояние."""

import json
from pathlib import Path

from dashboard.api.page import render_sprint
from dashboard.api.read import load_snapshot, sprint_view
from dashboard.api.preview import refresh

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "fixtures" / "ui" / "demo.json"


def test_demo_file_fills_the_sprint_screen(tmp_path: Path):
    result = refresh(DEMO, tmp_path)
    assert result.code == 0, result.message
    document = load_snapshot(result.path)
    page = render_sprint(sprint_view(document))
    metrics = {item["id"]: item for item in document["sprint"]["metrics"]}
    people = metrics["personLoad"]["detail"]["rows"]
    assert len(people) == 10
    assert people[2]["openKeys"] == []
    assert people[-1]["openKeys"] == []
    assert [item["issueKey"] for item in metrics["blockers"]["detail"]["items"]] == ["UI-4", "UI-5", "UI-6"]
    assert metrics["burndown"]["value"] is not None
    assert metrics["cycleTime"]["detail"]["perIssue"][0] == {"issueKey": "UI-1", "seconds": 14400}
    assert metrics["cycleTime"]["excluded"][0]["reason"] == "shorter-than-min-stay"
    assert document["coverage"]["storyPoints"] == "full"
    assert document["coverage"]["membership"] == "complete"
    assert document["sprint"]["trend"]["previous"]["sprintId"] == "s-prev"
    assert [point["date"] for point in document["sprint"]["trend"]["sparkline"]] == ["2026-09-10", "2026-09-16"]
    assert page.count('data-person="') == 10
    assert 'data-widget="burndown"' in page
    assert 'data-widget="previous"' in page
    assert "14400 с" in page
    assert "нет открытых" in page
    assert "asOf" not in page
    assert "Europe/Moscow" not in page
    assert "<h2>Команда</h2>" in page
    assert "Иванов" in page
    assert 'href="https://jira.example.com/browse/UI-4"' in page
    assert "Что вошло в число" in page
    assert "не оценка команды" in page
    assert "Y — количество SP" in page
    dates = [point["date"] for point in metrics["burndown"]["detail"]["points"]]
    assert "2026-09-12" not in dates
    assert "2026-09-13" not in dates
    assert dates[0] == "2026-09-07"
    assert dates[-1] == "2026-09-16"
    ivanov = people[0]
    assert ivanov["name"] == "Иванов Иван"
    assert "total" in ivanov
    assert "storyPoints" in ivanov
    trend = page[page.index('data-widget="trend"'):page.index('data-widget="issues"')]
    assert "2026-09-12" not in trend


def test_second_refresh_picks_up_an_edit(tmp_path: Path):
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    source = tmp_path / "demo.json"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    first = refresh(source, tmp_path / "work")
    assert first.code == 0
    data["bundle"]["issues"][10]["summary"] = "Новая подпись после правки"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    second = refresh(source, tmp_path / "work")
    assert second.code == 0
    page = render_sprint(sprint_view(load_snapshot(second.path)))
    assert "Новая подпись после правки" in page
