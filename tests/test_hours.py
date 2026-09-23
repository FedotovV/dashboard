"""Часы в статусе. 10:00–16:00 при перерыве 14:00–15:00 — это 5 часов, 18000 секунд."""

from datetime import date
from pathlib import Path

from dashboard.metrics.engine import compute
from tests.support import at, bundle, change, issue, team


def test_parallel_day_scales_after_splitting_inherited_and_own():
    old = issue("OLD")
    new = issue("NEW")
    data = bundle(
        [old, new],
        [
            change("OLD", "In Progress", "2026-09-07T07:00:00Z", "2026-09-07T09:00:00Z"),
            change("OLD", "In Progress", "2026-09-08T07:00:00Z", "2026-09-08T13:00:00Z"),
            change("NEW", "In Progress", "2026-09-08T07:00:00Z", "2026-09-08T13:00:00Z"),
        ],
        as_of=at("2026-09-08T16:00:00Z"),
    )
    config = team(period_start=date(2026, 9, 8))
    metric = next(item for item in compute(data, config, as_of=data.as_of).period_metrics if item.id == "statusHours")
    day = metric.detail["days"][0]
    assert day["rawSeconds"] == 36000
    assert day["scaledSeconds"] == 28800
    assert day["inheritedSeconds"] == 14400
    assert day["ownSeconds"] == 14400
    assert metric.detail["parallelism"] == 36000 / 28800
    assert metric.value == 1


def test_zero_elapsed_workdays_make_pace_null():
    data = bundle([issue("A-1")], as_of=at("2026-09-08T07:00:00Z"))
    config = team(period_start=date(2026, 9, 8))
    metric = next(item for item in compute(data, config, as_of=data.as_of).period_metrics if item.id == "statusHours")
    assert metric.value is None
    assert metric.detail["parallelism"] is None


def test_status_hours_are_not_named_utilization():
    root = Path(__file__).resolve().parents[1] / "src" / "dashboard"
    text = "\n".join(path.read_text().lower() for path in root.rglob("*.py"))
    assert "utilization" not in text
    assert "утилизац" not in text
