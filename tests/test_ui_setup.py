"""Мастер React пишет тот же документ, что POST /api/setup, и не читает секрет."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIELDS = (
    "team.name",
    "team.pm",
    "team.teamLead",
    "calendar.timezone",
    "calendar.workdays",
    "calendar.workStart",
    "calendar.workEnd",
    "calendar.breakMinutes",
    "calendar.breakStart",
    "calendar.hoursPerDay",
    "calendar.holidays",
    "calendar.extraWorkdays",
    "period.id",
    "period.start",
    "period.end",
    "sources.mode",
    "jira.deployment",
    "jira.baseUrl",
    "jira.boardId",
    "jira.sprintId",
    "jira.authEnv",
    "jira.storyPoints",
    "jira.epicLink",
    "workflow.usesDueDate",
    "taxonomy.priority",
    "epics.project",
    "epics.tech",
    "linkTypes",
    "other.prodLabel",
    "other.techLabel",
    "scope.issueTypes",
    "scope.projectKeys",
    "scope.countSubtasks",
    "metrics.minStaySeconds",
    "metrics.highPriorities",
    "metrics.maxAgeDays",
    "metrics.unknownWarnPct",
    "member.",
    "status.",
    "rule.",
)


def test_setup_form_names_the_server_fields_and_skips_the_secret():
    text = (ROOT / "frontend" / "src" / "SetupScreen.jsx").read_text(encoding="utf-8")
    api = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
    for name in FIELDS:
        assert name in text
    lowered = text.lower()
    assert "localstorage" not in lowered
    assert "os.environ" not in text
    assert "apply_form" not in text
    assert "Записать team.yaml" in text
    assert "Запустить сборку" not in text
    assert 'headers.Authorization = `Bearer ${token}`' in api or "Bearer ${token}" in api
    page = _render(_view("same"))
    assert 'name="jira.authEnv"' in page
    assert "JIRA_TOKEN" in page
    assert "super-secret-value" not in page
    assert "Хеш правил совпадает с manifest." in page
    assert "team.yaml записан" not in page
    assert "Хеш правил разошёлся с manifest." in _render(_view("diff"))
    assert "Файл manifest ещё не создан." in _render(_view("new"))
    assert "Manifest не подключён." in _render(_view("off"))
    locked = _render(_view("same", token=True))
    assert 'type="password"' in locked
    assert 'name="token"' in locked


def _render(view: dict) -> str:
    proc = subprocess.run(
        ["node", "frontend/render.mjs", "setup"],
        input=json.dumps(view),
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _view(state: str, token: bool = False) -> dict:
    return {
        "manifestState": state,
        "needsAcceptRecompute": state == "diff",
        "writeTokenRequired": token,
        "document": {
            "catalogVersion": 1,
            "team": {
                "id": "card",
                "name": "Карта",
                "members": [{"id": "dev", "name": "Разработчик", "allocation": 1}],
                "alumni": [],
            },
            "calendar": {"timezone": "Europe/Moscow", "workdays": [1, 2, 3, 4, 5], "breakMinutes": 60},
            "period": {"id": "2026-09", "start": "2026-09-07", "end": "2026-09-30"},
            "sources": {
                "mode": "fixture",
                "jira": {"deployment": "server", "baseUrl": "https://jira.example.com", "authEnv": "JIRA_TOKEN", "fields": {}},
            },
            "workflow": {"usesDueDate": True, "statusMap": [{"status": "Done", "category": "done", "role": "terminal"}]},
            "taxonomy": {"priority": ["project"], "epics": {"project": [], "tech": []}, "linkTypes": [], "rules": [], "otherSubtype": {}},
            "scope": {"issueTypes": ["Story"], "projectKeys": ["CARD"], "countSubtasks": False},
            "metrics": {"cycleTime": {"minStaySeconds": 900}, "hygiene": {}, "classification": {}},
        },
    }
