"""Документ периода читает файл слепка и не вызывает compute."""

from pathlib import Path

import pytest

from dashboard.api.read import RouteError, load_snapshot, metric_brief, team_view
from dashboard.metrics import engine
from tests.sprint_support import build_case


def test_team_view_copies_the_file_and_does_not_compute(tmp_path: Path, monkeypatch):
    path = build_case("scope-days", tmp_path, history=True)

    def boom(*_args, **_kwargs):
        raise AssertionError("маршрут вызвал compute")

    monkeypatch.setattr(engine, "compute", boom)
    document = load_snapshot(path)
    view = team_view(document)
    assert view["asOf"] == document["asOf"]
    assert view["timezone"] == document["timezone"]
    assert view["teamId"] == document["teamId"]
    assert view["coverage"] == document["coverage"]
    assert view["period"] == document["period"]
    assert view["trend"] == document["sprint"]["trend"]
    assert view["issues"] == document["sprint"]["issues"]
    assert view["completion"]["detail"] == {"done": 1, "committed": 2}
    brief = metric_brief(document, "classification")
    assert set(brief) == {"id", "version", "explain", "params"}
    assert "value" not in brief


def test_risk_score_is_not_a_metric(tmp_path: Path):
    path = build_case("scope-days", tmp_path)
    with pytest.raises(RouteError) as caught:
        metric_brief(load_snapshot(path), "riskScore")
    assert caught.value.status == 404


def test_screen_modules_do_not_import_the_engine():
    root = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "api"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "dashboard.metrics" not in text
    assert "compute(" not in text
