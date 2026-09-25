"""Собирает fixtures/ui/showcase.json. Повторный запуск перезаписывает файл.

Команда «Платёжная карта» закрыла прошлый спринт и дорабатывает текущий:
сегодня четверг 17 сентября 2026, спринт кончается в пятницу. Числа не случайны.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dashboard.metrics.ru_calendar import RU_NON_WORKING_2026  # noqa: E402

DEST = ROOT / "fixtures" / "ui" / "showcase.json"


def msk(day: str, hour: int, minute: int = 0) -> str:
    return f"{day}T{hour - 3:02d}:{minute:02d}:00Z"


def issue(
    key: str,
    status: str,
    assignee: str | None,
    summary: str,
    *,
    points: int | None,
    at_add: int,
    due: str | None,
    kind: str = "Story",
    created: str = "2026-09-01T06:00:00Z",
    resolution: str | None = None,
    priority: str = "Medium",
    labels: list[str] | None = None,
) -> dict:
    return {
        "id": key.lower(),
        "key": key,
        "summary": summary,
        "type": kind,
        "projectKey": "PAY",
        "status": status,
        "assigneeAccountId": assignee,
        "priority": priority,
        "storyPoints": points,
        "storyPointsAtAdd": at_add,
        "dueDate": due,
        "resolutionAt": resolution,
        "created": created,
        "labels": labels or [],
        "parentId": None,
        "subtask": False,
    }


def change(key: str, status: str, entered: str, exited: str | None = None) -> dict:
    return {"issueId": key.lower(), "status": status, "enteredAt": entered, "exitedAt": exited}


def membership(key: str, sprint: str, added: str, removed: str | None = None) -> dict:
    return {"issueId": key.lower(), "sprintId": sprint, "addedAt": added, "removedAt": removed}


def build_showcase() -> dict:
    start = "2026-09-07T06:00:00Z"
    issues = [
        issue("PAY-1", "Done", "sokolova", "Провести платёж до конца дня", points=8, at_add=8, due="2026-09-18", resolution=msk("2026-09-08", 18)),
        issue("PAY-2", "Done", "ivanov", "Показать маску карты", points=5, at_add=5, due="2026-09-16", resolution=msk("2026-09-14", 11)),
        issue("PAY-3", "Done", "petrova", "Закрыть сверку раньше срока", points=8, at_add=8, due="2026-09-18", resolution=msk("2026-09-11", 12)),
        issue("PAY-4", "Done", "sokolova", "Сохранить чек", points=5, at_add=5, due="2026-09-14", resolution=msk("2026-09-11", 15)),
        issue("PAY-5", "Done", "morozov", "Выпустить экран оплаты", points=8, at_add=8, due="2026-09-17", resolution=msk("2026-09-16", 16)),
        issue("PAY-6", "Canceled", "smirnov", "Отменённый эксперимент со скидкой", points=3, at_add=3, due="2026-09-18", resolution=msk("2026-09-09", 12), labels=["prod_op"]),
        issue("PAY-7", "In Progress", "ivanov", "Просроченный повтор платежа", points=2, at_add=2, due="2026-09-15"),
        issue("PAY-8", "On-hold", "smirnov", "Пауза: ждём ответ банка", points=1, at_add=1, due="2026-09-18"),
        issue("PAY-9", "In Progress", None, "Платёж без исполнителя", points=1, at_add=1, due="2026-09-18"),
        issue("PAY-10", "To Do", "volkov", "Высокий приоритет ещё в очереди", points=1, at_add=1, due="2026-09-18", priority="High"),
        issue("PAY-11", "In Progress", "lebedev", "Старая задача мая", points=1, at_add=1, due="2026-09-18", created="2026-05-01T06:00:00Z"),
        issue("PAY-12", "In Progress", "morozov", "Нет текущей оценки", points=None, at_add=1, due="2026-09-18"),
        issue("PAY-13", "Review", "petrova", "Ревью возврата", points=1, at_add=1, due="2026-09-18"),
        issue("PAY-14", "To Do", "kuznetsova", "Очередь без срока", points=1, at_add=1, due=None, labels=["регламент"]),
        issue("PAY-15", "In Progress", "sokolova", "Добить хвост оплаты", points=1, at_add=1, due="2026-09-18"),
        issue("PAY-16", "Done", "pavlova", "Короткий автопереход", points=2, at_add=2, due="2026-09-18", resolution=msk("2026-09-08", 10, 8)),
        issue("PAY-17", "In Progress", "kuznetsova", "Добавлена после старта", points=1, at_add=1, due="2026-09-18"),
        issue("PAY-18", "Review", "orlova", "Добавлена на ревью", points=1, at_add=1, due="2026-09-18"),
        issue("PAY-19", "To Do", "volkov", "Снята из спринта", points=2, at_add=2, due="2026-09-18"),
        issue("PAY-20", "In Progress", "sokolova", "Нет тайминга статуса", points=1, at_add=1, due="2026-09-18"),
        issue("PAY-22", "Done", "pavlova", "Закрыта без истории статуса", points=1, at_add=1, due="2026-09-18", resolution=msk("2026-09-16", 17)),
        issue("PAY-21", "Done", "vneshtat", "Час человека вне состава", points=1, at_add=1, due="2026-09-18", kind="Bug", resolution=msk("2026-09-16", 12), labels=["other_tech"]),
        issue("PAY-100", "In Progress", "morozov", "Оплата картой", points=None, at_add=0, due=None, kind="Epic", created="2026-08-01T06:00:00Z"),
        issue("PAY-200", "In Progress", "lebedev", "Наблюдаемость", points=None, at_add=0, due=None, kind="Epic", created="2026-08-01T06:00:00Z"),
    ]
    changes = [
        change("PAY-1", "In Progress", msk("2026-09-08", 10), msk("2026-09-08", 13)),
        change("PAY-1", "Done", msk("2026-09-08", 13), msk("2026-09-08", 16)),
        change("PAY-1", "In Progress", msk("2026-09-08", 16), msk("2026-09-08", 18)),
        change("PAY-1", "Done", msk("2026-09-08", 18)),
        change("PAY-2", "In Progress", msk("2026-09-09", 10), msk("2026-09-09", 16)),
        change("PAY-2", "Done", msk("2026-09-14", 11)),
        change("PAY-3", "In Progress", msk("2026-09-08", 10), msk("2026-09-08", 15)),
        change("PAY-3", "Review", msk("2026-09-08", 15), msk("2026-09-11", 12)),
        change("PAY-3", "Done", msk("2026-09-11", 12)),
        change("PAY-4", "In Progress", msk("2026-09-10", 10), msk("2026-09-11", 15)),
        change("PAY-4", "Done", msk("2026-09-11", 15)),
        change("PAY-5", "In Progress", msk("2026-09-14", 10), msk("2026-09-16", 16)),
        change("PAY-5", "Done", msk("2026-09-16", 16)),
        change("PAY-6", "In Progress", msk("2026-09-08", 10), msk("2026-09-09", 12)),
        change("PAY-6", "Canceled", msk("2026-09-09", 12)),
        change("PAY-7", "In Progress", msk("2026-09-09", 10)),
        change("PAY-8", "In Progress", msk("2026-09-09", 10), msk("2026-09-10", 11)),
        change("PAY-8", "On-hold", msk("2026-09-10", 11)),
        change("PAY-9", "In Progress", msk("2026-09-15", 10)),
        change("PAY-10", "To Do", msk("2026-09-07", 10)),
        change("PAY-11", "In Progress", msk("2026-08-20", 10)),
        change("PAY-12", "In Progress", msk("2026-09-16", 10)),
        change("PAY-13", "In Progress", msk("2026-09-14", 10), msk("2026-09-16", 14)),
        change("PAY-13", "Review", msk("2026-09-16", 14)),
        change("PAY-14", "To Do", msk("2026-09-07", 12)),
        change("PAY-15", "In Progress", msk("2026-09-16", 11)),
        change("PAY-16", "In Progress", msk("2026-09-08", 10), msk("2026-09-08", 10, 8)),
        change("PAY-16", "Done", msk("2026-09-08", 10, 8)),
        change("PAY-17", "In Progress", msk("2026-09-10", 10)),
        change("PAY-18", "Review", msk("2026-09-15", 10)),
        change("PAY-19", "To Do", msk("2026-09-07", 10), msk("2026-09-11", 10)),
        change("PAY-21", "In Progress", msk("2026-09-16", 10), msk("2026-09-16", 12)),
        change("PAY-21", "Done", msk("2026-09-16", 12)),
    ]
    current = "Спринт 24"
    memberships = [
        membership(key, current, start)
        for key in (
            "PAY-1", "PAY-2", "PAY-3", "PAY-4", "PAY-5", "PAY-6", "PAY-7", "PAY-8",
            "PAY-9", "PAY-10", "PAY-11", "PAY-12", "PAY-13", "PAY-14", "PAY-15", "PAY-16", "PAY-20", "PAY-22",
        )
    ]
    memberships.append(membership("PAY-17", current, msk("2026-09-10", 10)))
    memberships.append(membership("PAY-18", current, msk("2026-09-14", 10)))
    memberships.append(membership("PAY-19", current, start, msk("2026-09-11", 10)))
    return {
        "about": (
            "Команда «Платёжная карта». Прошлый спринт закрыт 4 сентября. "
            "Сейчас 17 сентября 2026, 18:00 МСК: текущий спринт кончается завтра. "
            "Запуск: python3 -m dashboard.api.preview --data fixtures/ui/showcase.json"
        ),
        "team": _team(),
        "bundle": {
            "bundleId": "paycard-2026-09-17",
            "asOf": "2026-09-17T15:00:00Z",
            "sourceWatermark": "showcase",
            "issues": issues,
            "statusChanges": changes,
            "memberships": memberships,
            "sprints": [
                {
                    "id": "Спринт 23",
                    "name": "Спринт 23",
                    "state": "closed",
                    "start": "2026-08-24",
                    "end": "2026-09-04",
                },
                {
                    "id": current,
                    "name": "Спринт 24",
                    "state": "active",
                    "start": "2026-09-07",
                    "end": "2026-09-18",
                },
            ],
            "links": [
                {"fromId": "pay-100", "toId": key.lower(), "type": "Child-Issue"}
                for key in ("PAY-1", "PAY-2", "PAY-5", "PAY-7", "PAY-12", "PAY-15")
            ]
            + [
                {"fromId": "pay-200", "toId": key.lower(), "type": "Child-Issue"}
                for key in ("PAY-8", "PAY-11", "PAY-13")
            ],
        },
        "edits": {
            "teamId": "paycard",
            "revision": 1,
            "projectReleases": [
                {"epicId": "PAY-100", "release": "2026.09"},
                {"epicId": "PAY-999", "release": "чужой"},
            ],
            "projectNotes": [
                {
                    "epicId": "PAY-100",
                    "text": "Релиз в пятницу. Хвост: просроченный платёж и пауза банка.",
                    "author": "Крылова Наталья",
                    "at": "2026-09-17T12:00:00Z",
                }
            ],
        },
        "history": [
            {
                "date": "2026-09-04",
                "document": {
                    "snapshotId": "paycard-2026-09-04",
                    "sprint": {
                        "id": "Спринт 23",
                        "metrics": [
                            {
                                "id": "sprintFlow",
                                "detail": {
                                    "byRole": {
                                        "active": 0,
                                        "wait": 0,
                                        "hold": 0,
                                        "queue": 0,
                                        "done": 14,
                                        "canceled": 1,
                                        "total": 15,
                                    }
                                },
                            }
                        ],
                    },
                },
            },
            {
                "date": "2026-09-08",
                "document": _flow_day("2026-09-08", done=1),
            },
            {
                "date": "2026-09-10",
                "document": _flow_day("2026-09-10", done=3),
            },
            {
                "date": "2026-09-15",
                "document": _flow_day("2026-09-15", done=5),
            },
        ],
    }


def _flow_day(day: str, done: int) -> dict:
    return {
        "snapshotId": f"paycard-{day}",
        "sprint": {
            "id": "Спринт 24",
            "metrics": [
                {
                    "id": "sprintFlow",
                    "detail": {
                        "byRole": {
                            "active": 6,
                            "wait": 1,
                            "hold": 1,
                            "queue": 3,
                            "done": done,
                            "canceled": 0,
                            "total": 11 + done,
                        }
                    },
                }
            ],
        },
    }


def _team() -> dict:
    people = [
        ("sokolova", "Соколова Елена", "dev", 1, None),
        ("ivanov", "Иванов Иван", "dev", 1, None),
        ("petrova", "Петрова Анна", "dev", 1, None),
        ("smirnov", "Смирнов Пётр", "dev", 1, None),
        ("volkov", "Волков Сергей", "dev", 1, None),
        ("lebedev", "Лебедев Николай", "dev", 1, None),
        ("morozov", "Морозов Дмитрий", "lead", 1, ["PAY-100"]),
        ("kuznetsova", "Кузнецова Ольга", "dev", 1, None),
        ("orlova", "Орлова Мария", "qa", 0.5, None),
        ("pavlova", "Павлова Ирина", "qa", 1, None),
        ("novikova", "Новикова Дарья", "dev", 1, None),
    ]
    members = []
    for person_id, name, role, allocation, leads in people:
        member = {
            "id": person_id,
            "name": name,
            "jiraUsername": person_id,
            "role": role,
            "allocation": allocation,
        }
        if leads:
            member["featureLeadOf"] = leads
        members.append(member)
    return {
        "version": 1,
        "catalogVersion": 1,
        "team": {
            "id": "paycard",
            "name": "Платёжная карта",
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
            "holidays": [day.isoformat() for day in sorted(RU_NON_WORKING_2026)],
            "extraWorkdays": [],
        },
        "period": {"id": "2026-09", "start": "2026-09-01", "end": "2026-09-30"},
        "sources": {
            "mode": "fixture",
            "jira": {
                "deployment": "server",
                "baseUrl": "https://jira.example.com",
                "boardId": "24",
                "sprintId": "Спринт 24",
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
            "epics": {"project": ["PAY-100"], "tech": ["PAY-200"]},
            "linkTypes": ["Child-Issue"],
            "rules": [{"category": "other", "when": {"label": "регламент"}}],
            "otherSubtype": {"prodLabel": "prod_op", "techLabel": "other_tech"},
        },
        "scope": {
            "issueTypes": ["Story", "Task", "Bug"],
            "projectKeys": ["PAY"],
            "countSubtasks": False,
        },
        "metrics": {
            "cycleTime": {"minStaySeconds": 900},
            "hygiene": {"highPriorities": ["High"], "maxAgeDays": 90},
            "classification": {"unknownWarnPct": 15},
        },
    }


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(build_showcase(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(DEST)


if __name__ == "__main__":
    main()
