"""Экран «Период» рисует поля слепка и сам их не считает."""

import shutil
from pathlib import Path

from dashboard.api.period import render_period
from dashboard.api.read import load_snapshot, team_view
from dashboard.orchestrator.build import BuildRequest, build
from tests.sprint_support import build_case

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "m1"


def test_unknown_banner_is_above_the_hours_ring_and_people_keep_the_path(tmp_path: Path):
    page = _page("classify", tmp_path)
    assert page.index('data-widget="unknown"') < page.index('data-widget="hours"')
    assert "Не разобрано 33.333333333333336%" in page
    assert "Разработчик" in page
    assert "https://jira.example.com/browse/A-1" in page
    start = page.index("browse/A-1")
    assert "голова p-1, проект" in page[start:page.index("</li>", start)]
    unknown = page.index("browse/U-1")
    row = page[page.rfind("<li", 0, unknown):page.index("</li>", unknown)]
    assert "нет головы" in row
    assert 'data-attention="true"' in row
    assert "utilization" not in page.lower()
    assert "утилизац" not in page.lower()
    assert "riskScore" not in page
    assert "<button" not in page


def test_hours_ring_uses_snapshot_seconds(tmp_path: Path):
    page = _page("parallel-day", tmp_path)
    assert 'class="ring"' in page
    assert "14400" in page
    assert "36000" in page
    assert "28800" in page
    assert "1.25" in page
    assert "не списание" in page
    assert 'data-diagnostic="ratio"' in page
    assert "utilization" not in page.lower()
    assert "утилизац" not in page.lower()


def test_missing_timings_hide_the_ring():
    page = render_period(
        {
            "teamId": "card",
            "coverage": {"timing": "none", "membership": "complete"},
            "period": {
                "id": "2026-09",
                "start": "2026-09-07",
                "end": "2026-09-30",
                "metrics": [
                    {
                        "id": "statusHours",
                        "value": None,
                        "detail": {"inheritedSeconds": 0, "ownSeconds": 0, "parallelism": None, "days": []},
                        "explain": "Часы в статусе, не списание.",
                    }
                ],
            },
            "issues": [],
        }
    )
    assert "coverage.timing = none" in page
    assert 'class="ring"' not in page
    assert "Пришли из прошлого" not in page


def test_epic_note_and_committed_completion_come_from_the_snapshot(tmp_path: Path):
    page = _page("edits-intact", tmp_path, edits=True)
    assert "2026-Q3" in page
    assert "Ждём макет" in page
    sprint = _page("scope-days", tmp_path)
    assert 'href="/"' in sprint
    assert "1 из 2" in sprint


def test_empty_epic_list_is_a_banner():
    page = render_period(
        {
            "teamId": "card",
            "coverage": {"timing": "full", "membership": "complete"},
            "period": {
                "id": "2026-09",
                "start": "2026-09-07",
                "end": "2026-09-30",
                "metrics": [
                    {
                        "id": "projectList",
                        "value": 0,
                        "warnings": ["no-epics"],
                        "detail": {"rows": []},
                    }
                ],
            },
            "issues": [],
            "completion": {"value": None, "detail": {}},
        }
    )
    assert "Список эпиков пуст" in page
    assert "<table" not in page
    assert "1 из" not in page


def test_incomplete_membership_hides_the_completion_fraction():
    page = render_period(
        {
            "teamId": "card",
            "coverage": {"timing": "full", "membership": "incomplete"},
            "period": {"id": "2026-09", "start": "2026-09-07", "end": "2026-09-30", "metrics": []},
            "issues": [],
            "completion": {"value": 0.5, "detail": {"done": 1, "committed": 2}},
        }
    )
    assert "1 из 2" not in page


def _page(case: str, tmp_path: Path, edits: bool = False) -> str:
    if not edits:
        path = build_case(case, tmp_path)
    else:
        source = FIXTURES / case
        edits_path = tmp_path / f"{case}-edits.json"
        shutil.copy(source / "edits.json", edits_path)
        result = build(
            BuildRequest(
                team_path=source / "team.yaml",
                bundle_path=source / "canonical.json",
                out_dir=tmp_path / case,
                edits_path=edits_path,
            )
        )
        assert result.code == 0, result.message
        path = result.path
    return render_period(team_view(load_snapshot(path)))
