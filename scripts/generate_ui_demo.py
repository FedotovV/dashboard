"""Один раз собирает fixtures/ui/demo.json. Повторный запуск перезаписывает правки.

Случайность только в оценках и формулировках. Роли статусов, десять человек,
состав спринта и причины блокеров зафиксированы, иначе экран теряет блоки.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "fixtures" / "ui" / "demo.json"

PEOPLE = (
    ("ivanov", "Иванов Иван", "dev", 1),
    ("petrova", "Петрова Анна", "dev", 1),
    ("smirnov", "Смирнов Пётр", "dev", 1),
    ("orlova", "Орлова Мария", "qa", 0.5),
    ("volkov", "Волков Сергей", "dev", 1),
    ("sokolova", "Соколова Елена", "dev", 1),
    ("morozov", "Морозов Дмитрий", "lead", 1),
    ("kuznetsova", "Кузнецова Ольга", "dev", 1),
    ("lebedev", "Лебедев Николай", "dev", 1),
    ("pavlova", "Павлова Ирина", "qa", 1),
)

SUMMARIES = (
    "Показать срок на карточке",
    "Пустое состояние списка",
    "Согласовать текст ошибки",
    "Починить сохранение черновика",
    "Добавить фильтр по исполнителю",
    "Сверить итог с составом на старте",
    "Убрать лишний запрос при открытии",
    "Описать правило отмены",
    "Проверить отпуск в календаре",
    "Собрать подпись к burndown",
    "Не терять заметку после сборки",
    "Развести ожидание и работу",
    "Закрыть хвост ревью",
    "Показать человека без задач",
    "Вернуть задачу из паузы",
    "Короткий автопереход статуса",
)


def msk(day: str, hour: int, minute: int = 0) -> str:
    """Часы Москвы, без перехода на летнее время."""
    return f"{day}T{hour - 3:02d}:{minute:02d}:00Z"


def issue(
    key: str,
    status: str,
    assignee: str | None,
    summary: str,
    *,
    points: int | None,
    at_add: int,
    due: str | None = None,
    resolution: str | None = None,
    created: str = "2026-09-07T06:00:00Z",
    priority: str = "Medium",
) -> dict:
    return {
        "id": key.lower(),
        "key": key,
        "summary": summary,
        "type": "Story",
        "projectKey": "UI",
        "status": status,
        "assigneeAccountId": assignee,
        "priority": priority,
        "storyPoints": points,
        "storyPointsAtAdd": at_add,
        "dueDate": due,
        "resolutionAt": resolution,
        "created": created,
        "labels": [],
        "parentId": None,
        "subtask": False,
    }


def change(key: str, status: str, entered: str, exited: str | None = None) -> dict:
    return {"issueId": key.lower(), "status": status, "enteredAt": entered, "exitedAt": exited}


def membership(key: str, added: str = "2026-09-07T06:00:00Z", removed: str | None = None) -> dict:
    return {"issueId": key.lower(), "sprintId": "s-current", "addedAt": added, "removedAt": removed}


def build_demo() -> dict:
    rng = random.Random(20260923)
    titles = list(SUMMARIES)
    rng.shuffle(titles)
    points = [rng.choice((1, 2, 3, 5, 8)) for _ in range(16)]

    def title(index: int) -> str:
        return titles[index]

    def pts(index: int) -> int:
        return points[index]

    reopen_done = msk("2026-09-08", 18)
    issues = [
        issue("UI-1", "Done", "ivanov", title(0), points=pts(0), at_add=pts(0), due="2026-09-15", resolution=reopen_done),
        issue("UI-2", "Done", "petrova", title(1), points=pts(1), at_add=pts(1), due="2026-09-09", resolution="2026-09-09T21:30:00Z"),
        issue("UI-3", "Canceled", "smirnov", title(2), points=pts(2), at_add=pts(2), due="2026-09-18", resolution=msk("2026-09-09", 12)),
        issue("UI-4", "In Progress", "orlova", title(3), points=pts(3), at_add=pts(3), due="2026-09-10"),
        issue("UI-5", "On-hold", "volkov", title(4), points=pts(4), at_add=pts(4), due="2026-09-18"),
        issue("UI-6", "In Progress", None, title(5), points=pts(5), at_add=pts(5), due="2026-09-18"),
        issue("UI-7", "To Do", "sokolova", title(6), points=pts(6), at_add=pts(6), due="2026-09-18", priority="High"),
        issue("UI-8", "In Progress", "morozov", title(7), points=None, at_add=3, due="2026-09-18"),
        issue("UI-9", "To Do", "kuznetsova", title(8), points=pts(8), at_add=pts(8), due=None),
        issue("UI-10", "In Progress", "lebedev", title(9), points=pts(9), at_add=pts(9), due="2026-09-18", created="2026-05-01T06:00:00Z"),
        issue("UI-11", "In Progress", "ivanov", title(10), points=pts(10), at_add=pts(10), due="2026-09-18"),
        issue("UI-12", "To Do", "volkov", title(11), points=pts(11), at_add=pts(11), due="2026-09-18"),
        issue("UI-13", "In Progress", "ivanov", title(12), points=8, at_add=3, due="2026-09-17"),
        issue("UI-15", "Review", "petrova", title(13), points=pts(13), at_add=pts(13), due="2026-09-18"),
        issue("UI-16", "Done", "ivanov", title(14), points=pts(14), at_add=pts(14), due="2026-09-20", resolution=msk("2026-09-08", 10, 8)),
        {
            "id": "ui-100",
            "key": "UI-100",
            "summary": "Путь платежа",
            "type": "Epic",
            "projectKey": "UI",
            "status": "In Progress",
            "assigneeAccountId": "morozov",
            "priority": "Medium",
            "storyPoints": None,
            "storyPointsAtAdd": None,
            "dueDate": None,
            "resolutionAt": None,
            "created": "2026-08-01T06:00:00Z",
            "labels": [],
            "parentId": None,
            "subtask": False,
        },
    ]
    changes = [
        change("UI-1", "In Progress", msk("2026-09-08", 10), msk("2026-09-08", 10, 10)),
        change("UI-1", "To Do", msk("2026-09-08", 10, 10), msk("2026-09-08", 11)),
        change("UI-1", "In Progress", msk("2026-09-08", 11), msk("2026-09-08", 13)),
        change("UI-1", "Done", msk("2026-09-08", 13), msk("2026-09-08", 16)),
        change("UI-1", "In Progress", msk("2026-09-08", 16), msk("2026-09-08", 18)),
        change("UI-1", "Done", reopen_done),
        change("UI-2", "In Progress", msk("2026-09-08", 10), msk("2026-09-08", 13)),
        change("UI-2", "Review", msk("2026-09-08", 15), msk("2026-09-08", 17)),
        change("UI-2", "Done", "2026-09-09T21:30:00Z"),
        change("UI-3", "In Progress", msk("2026-09-09", 10), msk("2026-09-09", 12)),
        change("UI-3", "Canceled", msk("2026-09-09", 12)),
        change("UI-4", "In Progress", msk("2026-09-09", 10)),
        change("UI-5", "On-hold", msk("2026-09-09", 11)),
        change("UI-6", "In Progress", msk("2026-09-09", 12)),
        change("UI-7", "To Do", msk("2026-09-07", 10)),
        change("UI-8", "In Progress", msk("2026-09-10", 10)),
        change("UI-9", "To Do", msk("2026-09-07", 11)),
        change("UI-10", "In Progress", msk("2026-09-08", 10)),
        change("UI-11", "In Progress", msk("2026-09-10", 11)),
        change("UI-12", "To Do", msk("2026-09-07", 12)),
        change("UI-13", "In Progress", msk("2026-09-11", 10)),
        change("UI-15", "Review", msk("2026-09-14", 10)),
        change("UI-16", "In Progress", msk("2026-09-08", 10), msk("2026-09-08", 10, 8)),
        change("UI-16", "Done", msk("2026-09-08", 10, 8)),
    ]
    memberships = [
        membership(key)
        for key in (
            "UI-1",
            "UI-2",
            "UI-3",
            "UI-4",
            "UI-5",
            "UI-6",
            "UI-7",
            "UI-8",
            "UI-9",
            "UI-10",
            "UI-13",
            "UI-15",
            "UI-16",
        )
    ]
    memberships.append(membership("UI-11", added=msk("2026-09-10", 10)))
    memberships.append(membership("UI-12", removed=msk("2026-09-14", 10)))
    flow = {
        "active": 0,
        "wait": 0,
        "hold": 0,
        "queue": 0,
        "done": 7,
        "canceled": 1,
        "total": 8,
    }
    earlier = {
        "active": 4,
        "wait": 1,
        "hold": 1,
        "queue": 2,
        "done": 1,
        "canceled": 0,
        "total": 9,
    }
    return {
        "about": "Редактируемый стенд экрана. Правьте этот файл и снова запустите python3 -m dashboard.api.preview. Повторный запуск scripts/generate_ui_demo.py перезапишет файл.",
        "team": _team(),
        "bundle": {
            "bundleId": "ui-demo",
            "asOf": "2026-09-16T16:00:00Z",
            "sourceWatermark": "ui-demo",
            "issues": issues,
            "statusChanges": changes,
            "memberships": memberships,
            "sprints": [
                {
                    "id": "s-prev",
                    "name": "Спринт 11",
                    "state": "closed",
                    "start": "2026-08-24",
                    "end": "2026-09-04",
                },
                {
                    "id": "s-current",
                    "name": "Спринт 12",
                    "state": "active",
                    "start": "2026-09-07",
                    "end": "2026-09-18",
                },
            ],
            "links": [
                {"fromId": "ui-100", "toId": "ui-1", "type": "Child-Issue"},
                {"fromId": "ui-100", "toId": "ui-13", "type": "Child-Issue"},
            ],
        },
        "history": [
            {
                "date": "2026-09-04",
                "document": {
                    "snapshotId": "ui-demo-2026-09-04",
                    "sprint": {
                        "id": "s-prev",
                        "metrics": [{"id": "sprintFlow", "detail": {"byRole": flow}}],
                    },
                },
            },
            {
                "date": "2026-09-10",
                "document": {
                    "snapshotId": "ui-demo-2026-09-10",
                    "sprint": {
                        "id": "s-current",
                        "metrics": [{"id": "sprintFlow", "detail": {"byRole": earlier}}],
                    },
                },
            },
        ],
    }


def _team() -> dict:
    members = []
    for person_id, name, role, allocation in PEOPLE:
        member = {
            "id": person_id,
            "name": name,
            "jiraUsername": person_id,
            "role": role,
            "allocation": allocation,
        }
        if person_id == "morozov":
            member["featureLeadOf"] = ["UI-100"]
        if person_id == "volkov":
            member["absences"] = [{"start": "2026-08-03", "end": "2026-08-14"}]
        members.append(member)
    return {
        "version": 1,
        "catalogVersion": 1,
        "team": {
            "id": "ui-demo",
            "name": "Демо стенд",
            "locale": "ru",
            "pm": "Крылова Наталья",
            "teamLead": "Морозов Дмитрий",
            "members": members,
            "alumni": [],
        },
        "calendar": {
            "timezone": "Europe/Moscow",
            "workdays": [1, 2, 3, 4, 5],
            "workStart": "10:00",
            "workEnd": "19:00",
            "breakMinutes": 60,
            "breakStart": "14:00",
            "hoursPerDay": 8,
            "holidays": [],
            "extraWorkdays": [],
        },
        "period": {"id": "2026-09", "start": "2026-09-01", "end": "2026-09-30"},
        "sources": {
            "mode": "fixture",
            "jira": {
                "deployment": "server",
                "baseUrl": "https://jira.example.com",
                "boardId": "12",
                "sprintId": "s-current",
                "authEnv": "JIRA_TOKEN",
                "fields": {"storyPoints": "customfield_10016", "epicLink": "customfield_10014"},
            },
        },
        "workflow": {
            "usesDueDate": True,
            "statusMap": [
                {"status": "To Do", "category": "todo", "role": "queue"},
                {"status": "In Progress", "category": "indeterminate", "role": "active"},
                {"status": "Review", "category": "indeterminate", "role": "wait"},
                {"status": "On-hold", "category": "indeterminate", "role": "hold"},
                {"status": "Done", "category": "done", "role": "terminal"},
                {"status": "Canceled", "category": "done", "role": "terminal", "outcome": "canceled"},
            ],
        },
        "taxonomy": {
            "priority": ["project", "tech"],
            "epics": {"project": ["UI-100"], "tech": ["UI-200"]},
            "linkTypes": ["Child-Issue"],
            "rules": [],
            "otherSubtype": {"prodLabel": "prod_op", "techLabel": "other_tech"},
        },
        "scope": {"issueTypes": ["Story", "Task", "Bug"], "projectKeys": ["UI"], "countSubtasks": False},
        "metrics": {
            "cycleTime": {"minStaySeconds": 900},
            "hygiene": {"highPriorities": ["High"], "maxAgeDays": 90},
            "classification": {"unknownWarnPct": 15},
        },
    }


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(build_demo(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(DEST)


if __name__ == "__main__":
    main()
