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
