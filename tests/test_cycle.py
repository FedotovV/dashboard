"""Цикл — сумма роли active. Ожидаемые секунды посчитаны по окну 10:00–19:00 и перерыву 14:00–15:00."""

from datetime import date

from dashboard.metrics.engine import compute
from tests.support import at, bundle, change, issue, membership, team


def _done_reopened():
    """Короткий заход, очередь, два длинных active, второй terminal после переоткрытия.

    11:00–13:00 = 7200 с. 16:00–18:00 = 7200 с. Итого 14400, не 7200 до первого закрытия.
    """
    return issue(
        "C-1",
        status="Done",
        due_date=date(2026, 9, 10),
        resolution_at=at("2026-09-09T20:30:00Z"),
    ), [
        change("C-1", "In Progress", "2026-09-08T07:00:00Z", "2026-09-08T07:10:00Z"),
        change("C-1", "To Do", "2026-09-08T07:10:00Z", "2026-09-08T08:00:00Z"),
        change("C-1", "In Progress", "2026-09-08T08:00:00Z", "2026-09-08T10:00:00Z"),
        change("C-1", "Done", "2026-09-08T10:00:00Z", "2026-09-08T13:00:00Z"),
        change("C-1", "In Progress", "2026-09-08T13:00:00Z", "2026-09-08T15:00:00Z"),
        change("C-1", "Done", "2026-09-08T15:00:00Z", None),
    ]


def test_cycle_drops_short_stay_queue_and_recomputes_after_reopen():
    done, changes = _done_reopened()
    data = bundle([done], changes, as_of=at("2026-09-08T16:00:00Z"))
    cycle = next(item for item in compute(data, team(), as_of=data.as_of).sprint_metrics if item.id == "cycleTime")
    assert cycle.detail["perIssue"] == [{"issueKey": "C-1", "seconds": 14400}]
    assert cycle.value == 14400 / 28800
    assert "900" in cycle.explain
    assert cycle.excluded == []
    waiting = issue("W-1", status="Done")
    waited = bundle(
        [waiting],
        [
            change("W-1", "Review", "2026-09-08T07:00:00Z", "2026-09-08T09:00:00Z"),
            change("W-1", "Done", "2026-09-08T09:00:00Z", None),
        ],
        as_of=at("2026-09-08T16:00:00Z"),
    )
    wait = next(item for item in compute(waited, team(), as_of=waited.as_of).sprint_metrics if item.id == "waitTime")
    assert wait.detail["perIssue"] == [{"issueKey": "W-1", "seconds": 7200}]


def test_only_short_stay_is_excluded():
    short = issue("S-1", status="Done")
    data = bundle(
        [short],
        [
            change("S-1", "In Progress", "2026-09-08T07:00:00Z", "2026-09-08T07:10:00Z"),
            change("S-1", "Done", "2026-09-08T07:10:00Z", None),
        ],
        as_of=at("2026-09-08T16:00:00Z"),
    )
    cycle = next(item for item in compute(data, team(), as_of=data.as_of).sprint_metrics if item.id == "cycleTime")
    assert cycle.population == []
    assert cycle.excluded == [{"issueKey": "S-1", "reason": "shorter-than-min-stay"}]
    assert cycle.value is None


def test_due_midnight_uses_team_calendar_date():
    early = issue("E-1", status="Done", due_date=date(2026, 9, 10), resolution_at=at("2026-09-09T20:30:00Z"))
    on_time = issue("N-1", status="Done", due_date=date(2026, 9, 10), resolution_at=at("2026-09-09T21:30:00Z"))
    data = bundle(
        [early, on_time],
        [
            change("E-1", "Done", "2026-09-09T20:30:00Z", None),
            change("N-1", "Done", "2026-09-09T21:30:00Z", None),
        ],
        memberships=[membership("E-1"), membership("N-1")],
        as_of=at("2026-09-10T16:00:00Z"),
    )
    rows = {item["key"]: item for item in compute(data, team(), as_of=data.as_of).issues}
    assert rows["E-1"]["closedBeforeDue"] is True
    assert rows["N-1"]["closedBeforeDue"] is False
