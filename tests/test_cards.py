"""Гигиена, блокеры, люди, burndown и список эпиков."""

from datetime import date

from dashboard.config.model import Absence, Epics
from dashboard.metrics.engine import compute
from tests.support import at, bundle, change, issue, member, membership, team


def test_hygiene_keeps_one_reason_and_does_not_flag_overdue():
    bare = issue("H-1", story_points=None, assignee_account_id=None, created=at("2026-01-01T07:00:00Z"), status="In Progress")
    no_owner = issue("H-2", story_points=3, story_points_at_add=3, assignee_account_id=None, status="In Progress")
    late = issue(
        "H-3",
        story_points=3,
        story_points_at_add=3,
        due_date=date(2026, 9, 8),
        status="In Progress",
    )
    data = bundle(
        [bare, no_owner, late],
        [
            change("H-1", "In Progress", "2026-09-09T07:00:00Z", None),
            change("H-2", "In Progress", "2026-09-09T07:00:00Z", None),
            change("H-3", "In Progress", "2026-09-09T07:00:00Z", None),
        ],
        as_of=at("2026-09-09T16:00:00Z"),
    )
    metric = next(item for item in compute(data, team(), as_of=data.as_of).sprint_metrics if item.id == "hygiene")
    reasons = {item["issueKey"]: item["reason"] for item in metric.detail["items"]}
    assert reasons["H-1"] == "no-story-points"
    assert reasons["H-2"] == "no-assignee"
    assert "H-3" not in reasons


def test_blockers_are_a_sorted_list_not_a_score():
    overdue = issue("B-1", due_date=date(2026, 9, 1), status="In Progress", story_points=1, story_points_at_add=1)
    hold = issue("B-2", status="On-hold", story_points=1, story_points_at_add=1)
    empty = issue("B-3", assignee_account_id=None, status="In Progress", story_points=1, story_points_at_add=1)
    data = bundle(
        [empty, hold, overdue],
        [
            change("B-1", "In Progress", "2026-09-09T07:00:00Z", None),
            change("B-2", "On-hold", "2026-09-09T07:00:00Z", None),
            change("B-3", "In Progress", "2026-09-09T07:00:00Z", None),
        ],
        as_of=at("2026-09-09T16:00:00Z"),
    )
    metric = next(item for item in compute(data, team(), as_of=data.as_of).sprint_metrics if item.id == "blockers")
    assert [item["issueKey"] for item in metric.detail["items"]] == ["B-1", "B-2", "B-3"]
    assert metric.detail["items"][0]["reasons"] == ["overdue"]
    assert "risk" not in metric.explain.lower()


def test_person_load_keeps_zero_and_skips_absence():
    idle = member("idle")
    away = member("away", absences=(Absence(start=date(2026, 9, 9), end=date(2026, 9, 9)),))
    data = bundle(
        [issue("P-1", assignee_account_id="dev", status="In Progress")],
        [change("P-1", "In Progress", "2026-09-09T07:00:00Z", None)],
        as_of=at("2026-09-09T16:00:00Z"),
    )
    config = team(members=(member(), idle, away))
    metric = next(item for item in compute(data, config, as_of=data.as_of).sprint_metrics if item.id == "personLoad")
    rows = {row["personId"]: row["openKeys"] for row in metric.detail["rows"]}
    assert rows["dev"] == ["P-1"]
    assert rows["idle"] == []
    assert "away" not in rows
    assert metric.value == 2


def test_person_row_counts_roles_and_points():
    done = issue("P-1", assignee_account_id="dev", status="Done", story_points=2, story_points_at_add=2)
    working = issue("P-2", assignee_account_id="dev", status="In Progress", story_points=3, story_points_at_add=3)
    queued = issue("P-3", assignee_account_id="dev", status="To Do", story_points=1, story_points_at_add=1)
    paused = issue("P-4", assignee_account_id="dev", status="On-hold", story_points=None, story_points_at_add=1)
    review = issue("P-5", assignee_account_id="dev", status="Review", story_points=5, story_points_at_add=5)
    canceled = issue("P-6", assignee_account_id="dev", status="Canceled", story_points=8, story_points_at_add=8)
    data = bundle(
        [done, working, queued, paused, review, canceled],
        [
            change("P-1", "Done", "2026-09-08T08:00:00Z", None),
            change("P-2", "In Progress", "2026-09-09T07:00:00Z", None),
            change("P-3", "To Do", "2026-09-07T07:00:00Z", None),
            change("P-4", "On-hold", "2026-09-09T07:00:00Z", None),
            change("P-5", "Review", "2026-09-09T10:00:00Z", None),
            change("P-6", "Canceled", "2026-09-08T12:00:00Z", None),
        ],
        as_of=at("2026-09-09T16:00:00Z"),
    )
    metric = next(item for item in compute(data, team(), as_of=data.as_of).sprint_metrics if item.id == "personLoad")
    row = metric.detail["rows"][0]
    assert row["openKeys"] == ["P-2", "P-3", "P-4", "P-5"]
    assert row["total"] == 6
    assert row["backlog"] == 1
    assert row["inProgress"] == 1
    assert row["paused"] == 1
    assert row["testing"] == 1
    assert row["done"] == 1
    assert row["canceled"] == 1
    assert row["storyPoints"] == 19
    assert row["openStoryPoints"] == 9
    assert row["pointsMissing"] == 1
    assert [item["key"] for item in row["issues"]] == ["P-1", "P-2", "P-3", "P-4", "P-5", "P-6"]


def test_burndown_skips_weekends_and_russian_holidays():
    from datetime import date

    from dashboard.config.model import Calendar
    from dashboard.metrics.ru_calendar import chart_workday

    data = bundle(
        [issue("D-1", status="Done", story_points=5, story_points_at_add=5)],
        [change("D-1", "Done", "2026-09-08T08:00:00Z", None)],
        as_of=at("2026-09-14T16:00:00Z"),
    )
    # bundle() sprint is Sep 7–18. 14 Sep is Monday, so Saturday 12 and Sunday 13 must be absent.
    metric = next(item for item in compute(data, team(), as_of=data.as_of).sprint_metrics if item.id == "burndown")
    dates = [point["date"] for point in metric.detail["points"]]
    assert dates == ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11", "2026-09-14"]
    assert "2026-09-12" not in dates
    assert "2026-09-13" not in dates
    calendar = team().calendar
    assert chart_workday(date(2026, 1, 9), calendar) is False
    assert chart_workday(date(2026, 11, 4), calendar) is False
    assert chart_workday(date(2026, 3, 9), calendar) is False
    weekend = Calendar(
        timezone=calendar.timezone,
        workdays=calendar.workdays,
        work_start=calendar.work_start,
        work_end=calendar.work_end,
        break_minutes=calendar.break_minutes,
        break_start=calendar.break_start,
        hours_per_day=calendar.hours_per_day,
        holidays=calendar.holidays,
        extra_workdays=frozenset({date(2026, 9, 12)}),
    )
    assert chart_workday(date(2026, 9, 12), weekend) is True
    assert chart_workday(date(2026, 5, 1), weekend) is False


def test_burndown_uses_points_at_add_not_the_later_estimate():
    done = issue("D-1", status="Done", story_points=8, story_points_at_add=5)
    open_issue = issue("O-1", status="In Progress", story_points=3, story_points_at_add=3)
    data = bundle(
        [done, open_issue],
        [
            change("D-1", "Done", "2026-09-08T08:00:00Z", None),
            change("O-1", "In Progress", "2026-09-07T07:00:00Z", None),
        ],
        as_of=at("2026-09-09T16:00:00Z"),
    )
    computed = compute(data, team(), as_of=data.as_of)
    metric = next(item for item in computed.sprint_metrics if item.id == "burndown")
    assert computed.coverage["storyPoints"] == "full"
    assert metric.value == 3
    assert metric.detail["points"][-1]["actual"] == 3


def test_without_story_points_burndown_is_null_and_issue_points_are_null():
    data = bundle(
        [issue("N-1", story_points=5, story_points_at_add=5)],
        [change("N-1", "In Progress", "2026-09-09T07:00:00Z", None)],
        as_of=at("2026-09-09T16:00:00Z"),
    )
    computed = compute(data, team(story_points_field=None), as_of=data.as_of)
    metric = next(item for item in computed.sprint_metrics if item.id == "burndown")
    assert computed.coverage["storyPoints"] == "off"
    assert metric.value is None
    assert computed.issues[0]["storyPoints"] is None


def test_empty_epic_list_is_a_warning():
    taxonomy = team().taxonomy
    empty = type(taxonomy)(
        priority=taxonomy.priority,
        epics=Epics(project=(), tech=()),
        link_types=taxonomy.link_types,
        rules=taxonomy.rules,
        prod_label=taxonomy.prod_label,
        tech_label=taxonomy.tech_label,
    )
    data = bundle([issue("Z-1")], as_of=at("2026-09-09T16:00:00Z"))
    metric = next(
        item
        for item in compute(data, team(taxonomy=empty), as_of=data.as_of).period_metrics
        if item.id == "projectList"
    )
    assert metric.value == 0
    assert metric.warnings == ["no-epics"]
    assert metric.detail["rows"] == []
