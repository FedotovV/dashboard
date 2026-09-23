"""Состав спринта. Старт 2026-09-07: день 3 — 9 сентября, день 7 — 13 сентября."""

from dashboard.metrics.engine import compute
from dashboard.metrics.parse import Membership
from tests.support import at, bundle, change, issue, membership, team


def _bundle():
    committed = issue("C-1", status="Done")
    canceled = issue("X-1", status="Canceled")
    added = issue("A-1", status="In Progress")
    removed = issue("R-1", status="To Do")
    issues = [committed, canceled, added, removed]
    changes = [
        change("C-1", "Done", "2026-09-08T08:00:00Z", None),
        change("X-1", "Canceled", "2026-09-08T08:00:00Z", None),
        change("A-1", "In Progress", "2026-09-09T07:00:00Z", None),
        change("R-1", "To Do", "2026-09-07T07:00:00Z", None),
    ]
    memberships = [
        membership("C-1", "2026-09-07T06:00:00Z"),
        membership("X-1", "2026-09-07T06:00:00Z"),
        membership("A-1", "2026-09-09T07:00:00Z"),
        membership("R-1", "2026-09-07T06:00:00Z", removed="2026-09-13T07:00:00Z"),
    ]
    return bundle(issues, changes, memberships, as_of=at("2026-09-14T16:00:00Z"))


def test_add_on_day_3_remove_on_day_7_and_canceled_stays_in_denominator():
    computed = compute(_bundle(), team(), as_of=at("2026-09-14T16:00:00Z"))
    flow = next(item for item in computed.sprint_metrics if item.id == "sprintFlow")
    scope = next(item for item in computed.sprint_metrics if item.id == "scopeChange")
    completion = next(item for item in computed.sprint_metrics if item.id == "completionVsCommitted")
    assert flow.detail["byRole"] == {
        "active": 1,
        "wait": 0,
        "hold": 0,
        "queue": 0,
        "done": 1,
        "canceled": 1,
        "total": 3,
    }
    assert scope.detail["committedKeys"] == ["C-1", "X-1"]
    assert scope.detail["addedKeys"] == ["A-1"]
    assert scope.detail["removedKeys"] == ["R-1"]
    assert completion.detail == {"done": 1, "committed": 2}
    assert completion.value == 0.5
    assert "X-1" not in completion.population


def test_missing_added_at_nulls_scope_numbers():
    data = bundle(
        [issue("C-1")],
        memberships=[Membership(issue_id="C-1", sprint_id="s", added_at=None, removed_at=None)],
        as_of=at("2026-09-09T16:00:00Z"),
    )
    scope = next(item for item in compute(data, team(), as_of=data.as_of).sprint_metrics if item.id == "scopeChange")
    assert scope.detail["committed"] is None
    assert scope.detail["added"] is None
    assert scope.detail["removed"] is None
    assert compute(data, team(), as_of=data.as_of).coverage["membership"] == "incomplete"
