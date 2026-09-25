"""React-экран копирует состав, поток и цикл из слепка."""

import json
import subprocess
from pathlib import Path

from dashboard.api.read import load_snapshot, sprint_view
from tests.sprint_support import FIXTURES, build_case

ROOT = Path(__file__).resolve().parents[1]


def _page(path: Path) -> str:
    return _render(sprint_view(load_snapshot(path)))


def _render(view: dict) -> str:
    proc = subprocess.run(
        ["node", "frontend/render.mjs"],
        input=json.dumps(view),
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_scope_days_shows_composition_and_flow(tmp_path: Path):
    expected = json.loads((FIXTURES / "scope-days" / "expected.snapshot.json").read_text())
    page = _page(build_case("scope-days", tmp_path, history=True))
    scope = expected["sprint"]["metrics"][1]["detail"]
    assert 'data-scope="committed"' in page
    assert _card_number(page, "committed") == str(scope["committed"])
    assert _card_number(page, "added") == str(scope["added"])
    assert _card_number(page, "removed") == str(scope["removed"])
    assert _card_number(page, "canceled") == "1"
    assert "1 из 2" in page
    assert "всего минус старт" not in page
    assert 'data-widget="flow"' in page
    assert 'data-widget="timing"' in page


def test_cycle_reopen_shows_explain_and_stored_seconds(tmp_path: Path):
    page = _page(build_case("cycle-reopen", tmp_path))
    card = page[page.index('data-metric="cycleTime"'):page.index('data-metric="waitTime"')]
    assert card.count("900") == 1
    assert "14400 с" in card
    assert "nominalSeconds" not in page
    assert "workSeconds" not in page
    assert "Что вошло в число" in page


def test_incomplete_membership_does_not_invent_scope():
    page = _render(
        {
            "asOf": "2026-09-09T16:00:00Z",
            "timezone": "Europe/Moscow",
            "teamId": "card",
            "coverage": {
                "timing": "none",
                "unknownPct": None,
                "storyPoints": "off",
                "assigneeMatchPct": None,
                "membership": "incomplete",
            },
            "sprint": {
                "id": "s",
                "start": "2026-09-07",
                "end": "2026-09-18",
                "metrics": [
                    {
                        "id": "scopeChange",
                        "value": None,
                        "detail": {"committed": None, "added": None, "removed": None},
                    },
                    {
                        "id": "completionVsCommitted",
                        "value": None,
                        "detail": {"done": None, "committed": None},
                    },
                    {
                        "id": "sprintFlow",
                        "detail": {
                            "byRole": {
                                "active": 0,
                                "wait": 0,
                                "hold": 0,
                                "queue": 0,
                                "done": 0,
                                "canceled": 0,
                                "total": 0,
                            }
                        },
                    },
                ],
                "issues": [],
                "trend": {"previous": None, "sparkline": [{"date": "2026-09-09", "done": 0}]},
            },
        }
    )
    assert "coverage.timing = none" in page
    assert "coverage.membership = incomplete" in page
    assert "состав на старте не собран" in page
    assert "всего минус старт" not in page
    assert _card_number(page, "committed") == "—"


def test_frontend_sources_do_not_calculate():
    root = ROOT / "frontend" / "src"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file()).lower()
    assert "dashboard.metrics" not in text
    assert "riskscore" not in text
    assert "utilization" not in text
    assert "утилизац" not in text


def _card_number(page: str, token: str) -> str:
    marker = f'data-scope="{token}"' if token in {"committed", "added", "removed"} else f'data-role="{token}"'
    start = page.index(marker)
    num = page.index('class="num"', start)
    open_tag = page.index(">", num)
    close_tag = page.index("</span>", open_tag)
    return page[open_tag + 1:close_tag]
