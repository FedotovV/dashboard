from datetime import date, time, timedelta
from pathlib import Path

import pytest

from dashboard.config.load import ConfigError, load_team
from dashboard.config.hash import input_hashes, rule_hash
from dashboard.metrics.time import elapsed_workdays, is_workday, work_seconds
from tests.support import at, calendar

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "schema" / "examples"


def test_example_team_loads_without_reading_secrets():
    config = load_team(EXAMPLES / "team.example.yaml")
    assert config.team_id == "payments-card"
    assert config.auth_env == "JIRA_TOKEN"
    assert config.deployment == "server"
    assert config.story_points_field == "customfield_10016"
    assert config.min_stay_seconds == 900
    assert config.jira_base_url == "https://jira.example.com"


def test_no_points_field_is_off_and_break_is_centered():
    config = load_team(EXAMPLES / "team.no-points.yaml")
    assert config.story_points_field is None
    assert config.deployment == "cloud"
    assert config.calendar.break_start == time(13, 0)


def test_unknown_catalog_version_is_rejected(tmp_path: Path):
    text = (EXAMPLES / "team.example.yaml").read_text().replace("catalogVersion: 1", "catalogVersion: 2", 1)
    path = tmp_path / "team.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError, match="catalogVersion"):
        load_team(path)


def test_unknown_formula_version_is_rejected(tmp_path: Path):
    text = (EXAMPLES / "team.example.yaml").read_text().replace(
        "cycleTime:\n    minStaySeconds: 900",
        "cycleTime:\n    version: 2\n    minStaySeconds: 900",
        1,
    )
    path = tmp_path / "team.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError, match="cycleTime"):
        load_team(path)


def test_window_must_match_hours(tmp_path: Path):
    text = (EXAMPLES / "team.example.yaml").read_text().replace("hoursPerDay: 8", "hoursPerDay: 7", 1)
    path = tmp_path / "team.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError, match="hoursPerDay"):
        load_team(path)


def test_break_outside_window_is_rejected(tmp_path: Path):
    text = (EXAMPLES / "team.example.yaml").read_text().replace(
        'workEnd: "18:00"\n  breakMinutes: 0\n  hoursPerDay: 8',
        'workEnd: "18:00"\n  breakMinutes: 60\n  breakStart: "17:30"\n  hoursPerDay: 7',
        1,
    )
    path = tmp_path / "team.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError, match="перерыв"):
        load_team(path)


def test_rule_hash_changes_only_with_the_edited_section():
    config = load_team(EXAMPLES / "team.example.yaml")
    again = load_team(EXAMPLES / "team.example.yaml")
    assert rule_hash(config) == rule_hash(again)
    assert input_hashes(config) == input_hashes(again)
    text = (EXAMPLES / "team.example.yaml").read_text().replace("On-hold", "Blocked", 1)
    path_note = config.raw_workflow["statusMap"]
    assert any(row["status"] == "On-hold" for row in path_note)
    # Другой статус меняет workflow и общий хеш, календарь остаётся.
    from dashboard.config.load import load_team as load
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "team.yaml"
        path.write_text(text)
        changed = load(path)
    assert input_hashes(changed)["calendar"] == input_hashes(config)["calendar"]
    assert input_hashes(changed)["workflow"] != input_hashes(config)["workflow"]
    assert rule_hash(changed) != rule_hash(config)


def test_holiday_is_not_a_workday_and_extra_day_is():
    day = date(2026, 9, 8)
    cal = calendar(holidays=frozenset({day}))
    assert is_workday(day, cal) is False
    saturday = date(2026, 9, 12)
    assert is_workday(saturday, calendar()) is False
    assert is_workday(saturday, calendar(extra_workdays=frozenset({saturday}))) is True


def test_work_seconds_skip_break_holiday_and_use_team_midnight():
    cal = calendar()
    assert work_seconds(at("2026-09-08T07:00:00Z"), at("2026-09-08T08:00:00Z"), cal) == 3600
    assert work_seconds(at("2026-09-08T10:00:00Z"), at("2026-09-08T12:00:00Z"), cal) == 3600
    assert work_seconds(at("2026-09-08T11:00:00Z"), at("2026-09-08T12:00:00Z"), cal) == 0
    holiday = calendar(holidays=frozenset({date(2026, 9, 8)}))
    assert work_seconds(at("2026-09-08T07:00:00Z"), at("2026-09-08T09:00:00Z"), holiday) == 0
    saturday = date(2026, 9, 12)
    extra = calendar(extra_workdays=frozenset({saturday}))
    assert work_seconds(at("2026-09-12T07:00:00Z"), at("2026-09-12T08:00:00Z"), extra) == 3600
    assert work_seconds(at("2026-09-12T07:00:00Z"), at("2026-09-12T08:00:00Z"), cal) == 0
    # 21:00Z — это 00:00 Москвы, не рабочее окно. 07:00Z — 10:00 Москвы.
    assert work_seconds(at("2026-09-09T21:00:00Z"), at("2026-09-09T22:00:00Z"), cal) == 0
    assert work_seconds(at("2026-09-09T07:00:00Z"), at("2026-09-09T08:00:00Z"), cal) == 3600


def test_centered_break_is_cut_out_of_the_window():
    cal = calendar(work_start=time(9, 0), work_end=time(18, 0), break_minutes=60, break_start=time(13, 0), hours_per_day=8)
    assert work_seconds(at("2026-09-08T10:00:00Z"), at("2026-09-08T11:00:00Z"), cal) == 0
    assert work_seconds(at("2026-09-08T09:00:00Z"), at("2026-09-08T10:00:00Z"), cal) == 3600


def test_elapsed_workday_starts_only_after_work_end():
    cal = calendar()
    morning = at("2026-09-08T07:00:00Z")
    evening = at("2026-09-08T16:00:00Z")
    assert elapsed_workdays(date(2026, 9, 8), date(2026, 9, 30), morning, cal) == []
    assert elapsed_workdays(date(2026, 9, 8), date(2026, 9, 30), evening, cal) == [date(2026, 9, 8)]


def test_half_open_end_is_excluded():
    cal = calendar(break_minutes=0, break_start=None, work_end=time(18, 0), hours_per_day=8)
    start = at("2026-09-08T07:00:00Z")
    assert work_seconds(start, start, cal) == 0
    assert work_seconds(start, start + timedelta(hours=1), cal) == 3600
