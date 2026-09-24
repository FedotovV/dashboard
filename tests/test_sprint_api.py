"""Документ маршрута читает файл слепка и не вызывает compute."""

import json
from pathlib import Path

import pytest

from dashboard.api.read import RouteError, load_snapshot, metric_brief, resolve_snapshot, sprint_view
from dashboard.metrics import engine
from tests.sprint_support import build_case


def test_sprint_view_copies_the_file_and_does_not_compute(tmp_path: Path, monkeypatch):
    path = build_case("scope-days", tmp_path, history=True)

    def boom(*_args, **_kwargs):
        raise AssertionError("маршрут вызвал compute")

    monkeypatch.setattr(engine, "compute", boom)
    document = load_snapshot(path)
    view = sprint_view(document)
    assert view == {
        "asOf": document["asOf"],
        "timezone": document["timezone"],
        "teamId": document["teamId"],
        "coverage": document["coverage"],
        "jiraBaseUrl": document["jiraBaseUrl"],
        "sprint": document["sprint"],
    }
    brief = metric_brief(document, "cycleTime")
    assert set(brief) == {"id", "version", "explain", "params"}
    assert "value" not in brief


def test_unknown_metric_is_missing(tmp_path: Path):
    path = build_case("scope-days", tmp_path)
    document = load_snapshot(path)
    with pytest.raises(RouteError) as caught:
        metric_brief(document, "riskScore")
    assert caught.value.status == 404


def test_period_metric_brief_has_no_value(tmp_path: Path):
    path = build_case("scope-days", tmp_path)
    document = load_snapshot(path)
    brief = metric_brief(document, "statusHours")
    assert set(brief) == {"id", "version", "explain", "params"}
    assert "value" not in brief


def test_latest_file_is_chosen_by_date(tmp_path: Path):
    path = build_case("no-points", tmp_path)
    assert resolve_snapshot(path.parent.parent, "card") == path


def test_missing_snapshot_is_404(tmp_path: Path):
    with pytest.raises(RouteError) as caught:
        resolve_snapshot(tmp_path, "card")
    assert caught.value.status == 404


def test_broken_snapshot_is_422_and_not_replaced(tmp_path: Path):
    path = build_case("no-points", tmp_path)
    broken = path.parent / "2026-09-20.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(RouteError) as caught:
        load_snapshot(resolve_snapshot(path.parent.parent, "card"))
    assert caught.value.status == 422
    assert "coverage" not in caught.value.message
    assert json.loads(path.read_text())["teamId"] == "card"
