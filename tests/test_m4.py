"""M4: collect fixture/file и одна команда. Ответ API сверяется с ожидаемым JSON."""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

import pytest
import yaml

from dashboard.__main__ import main
from dashboard.api.serve import make_server
from dashboard.connectors import CollectError, collect_bundle
from dashboard.orchestrator.build import BuildRequest, build
from dashboard.orchestrator.collect import CollectRequest, collect
from dashboard.orchestrator.run import RunRequest, run
from tests.test_gold import FORMULA_CASES, _assert_locked, _expected

ROOT = Path(__file__).resolve().parents[1]
M1 = ROOT / "fixtures" / "m1"
FILE_CASE = ROOT / "fixtures" / "m4" / "file-sprint"
CONNECTORS = ROOT / "src" / "dashboard" / "connectors"
NETWORK = ("urllib", "http", "socket", "requests")
FORBIDDEN = (
    "socket",
    "requests",
    "dashboard.metrics",
    "dashboard.edits",
    "dashboard.snapshotstore",
    "dashboard.api",
    "dashboard.orchestrator",
)


def test_connectors_do_not_import_network_or_metrics():
    for path in CONNECTORS.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                assert not module.startswith(FORBIDDEN), (path.name, module)
                if path.name != "http.py":
                    assert not module.startswith(NETWORK), (path.name, module)


def test_live_without_token_writes_nothing(tmp_path: Path):
    team = _team_with_mode(tmp_path, "live")
    bundle = tmp_path / "bundle.json"
    result = collect(CollectRequest(team, FILE_CASE / "raw", bundle, environ={}))
    assert result.code == 2
    assert "токен" in result.message
    assert not bundle.exists()


def test_fixture_collect_keeps_the_document(tmp_path: Path):
    source = M1 / "due-midnight" / "canonical.json"
    dest = tmp_path / "bundle.json"
    result = collect(CollectRequest(M1 / "due-midnight" / "team.yaml", source, dest))
    assert result.code == 0, result.message
    assert result.bundle == json.loads(source.read_text())
    again = tmp_path / "again.json"
    second = collect(CollectRequest(M1 / "due-midnight" / "team.yaml", source, again))
    assert dest.read_bytes() == again.read_bytes()
    assert second.code == 0


def test_fixture_directory_is_rejected(tmp_path: Path):
    result = collect(CollectRequest(M1 / "due-midnight" / "team.yaml", FILE_CASE / "raw", tmp_path / "bundle.json"))
    assert result.code == 2
    assert not (tmp_path / "bundle.json").exists()


def test_file_collect_matches_expected_canonical(tmp_path: Path):
    expected = json.loads((FILE_CASE / "expected.canonical.json").read_text())
    dest = tmp_path / "bundle.json"
    result = collect(CollectRequest(FILE_CASE / "team.yaml", FILE_CASE / "raw", dest))
    assert result.code == 0, result.message
    assert result.bundle == expected
    direct = build(
        BuildRequest(
            team_path=FILE_CASE / "team.yaml",
            bundle_path=FILE_CASE / "expected.canonical.json",
            out_dir=tmp_path / "direct",
        )
    )
    produced = build(
        BuildRequest(team_path=FILE_CASE / "team.yaml", bundle_path=dest, out_dir=tmp_path / "produced")
    )
    assert direct.code == 0 and produced.code == 0
    assert produced.path.read_bytes() == direct.path.read_bytes()


def test_file_import_reads_cloud_account_and_sprint_name(tmp_path: Path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "meta.json").write_text(
        json.dumps({"bundleId": "cloud", "asOf": "2026-09-10T16:00:00Z", "sourceWatermark": "cloud"})
    )
    (raw / "search.json").write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "id": 42,
                        "key": "C-42",
                        "fields": {
                            "summary": "Облако",
                            "issuetype": {"name": "Story", "subtask": False},
                            "project": {"key": "CARD"},
                            "status": {"name": "In Progress"},
                            "assignee": {"name": "someone", "accountId": "acc-1"},
                            "created": "2026-09-07T07:00:00Z",
                            "labels": [],
                        },
                    }
                ]
            }
        )
    )
    (raw / "changelogs.json").write_text(
        json.dumps(
            {
                "42": {
                    "histories": [
                        {
                            "created": "2026-09-07T06:00:00Z",
                            "items": [
                                {
                                    "field": "Sprint",
                                    "from": None,
                                    "fromString": "",
                                    "to": None,
                                    "toString": "Спринт",
                                }
                            ],
                        }
                    ]
                }
            }
        )
    )
    (raw / "sprints.json").write_text(
        json.dumps(
            [
                {
                    "id": "s",
                    "name": "Спринт",
                    "state": "active",
                    "startDate": "2026-09-07",
                    "endDate": "2026-09-18",
                }
            ]
        )
    )
    sources = {
        "jira": {
            "deployment": "cloud",
            "fields": {"storyPoints": None},
        }
    }
    bundle = collect_bundle("file", raw, sources)
    issue = bundle["issues"][0]
    assert issue["id"] == "42"
    assert issue["assigneeAccountId"] == "acc-1"
    assert issue["storyPoints"] is None
    assert bundle["memberships"] == [
        {"issueId": "42", "sprintId": "s", "addedAt": "2026-09-07T06:00:00Z", "removedAt": None}
    ]


def test_live_without_address_does_not_return_a_bundle(tmp_path: Path):
    with pytest.raises(CollectError):
        collect_bundle("live", tmp_path, {"jira": {"deployment": "server"}}, environ={})


@pytest.mark.parametrize("case", FORMULA_CASES)
def test_run_matches_gold_snapshot(case: str, tmp_path: Path):
    source = M1 / case
    out = tmp_path / "out"
    history = source / "history"
    if history.exists():
        shutil.copytree(history, out / "card")
    edits = None
    if (source / "edits.json").exists():
        edits = tmp_path / "edits.json"
        shutil.copy(source / "edits.json", edits)
    edits_before = edits.read_bytes() if edits else None
    result = run(RunRequest(source / "team.yaml", source / "canonical.json", out, edits_path=edits))
    assert result.code == 0, result.message
    _assert_locked(json.loads(result.path.read_text()), _expected(case))
    if edits_before is not None:
        assert edits.read_bytes() == edits_before
    if case == "write-once":
        payload = result.path.read_bytes()
        second = run(RunRequest(source / "team.yaml", source / "canonical.json", out, edits_path=edits))
        assert second.code == 0
        assert result.path.read_bytes() == payload


def test_run_snapshot_bytes_match_build(tmp_path: Path):
    source = M1 / "due-midnight"
    produced = run(RunRequest(source / "team.yaml", source / "canonical.json", tmp_path / "run"))
    direct = build(
        BuildRequest(
            team_path=source / "team.yaml",
            bundle_path=source / "canonical.json",
            out_dir=tmp_path / "build",
        )
    )
    assert produced.code == 0 and direct.code == 0
    assert produced.path.read_bytes() == direct.path.read_bytes()


def test_rules_changed_still_stops_before_a_snapshot(tmp_path: Path):
    source = M1 / "rules-changed"
    manifest = tmp_path / "manifest.json"
    shutil.copy(source / "manifest.json", manifest)
    before = manifest.read_bytes()
    out = tmp_path / "out"
    result = run(
        RunRequest(
            source / "team.yaml",
            source / "canonical.json",
            out,
            manifest_path=manifest,
        )
    )
    assert result.code == 3
    assert not (out / "card").exists()
    assert manifest.read_bytes() == before


def test_cli_run_writes_the_gold_day(tmp_path: Path):
    source = M1 / "due-midnight"
    out = tmp_path / "out"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dashboard",
            "run",
            "--team",
            str(source / "team.yaml"),
            "--source",
            str(source / "canonical.json"),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    built = json.loads((out / "card" / "2026-09-10.json").read_text())
    _assert_locked(built, _expected("due-midnight"))


def test_external_serve_is_refused_before_collect(tmp_path: Path):
    source = M1 / "due-midnight"
    out = tmp_path / "out"
    code = main(
        [
            "run",
            "--team",
            str(source / "team.yaml"),
            "--source",
            str(source / "canonical.json"),
            "--out",
            str(out),
            "--serve",
            "--host",
            "0.0.0.0",
        ]
    )
    assert code == 2
    assert not out.exists()
    assert main(["serve", "--snapshots", str(tmp_path), "--team", "card", "--host", "10.0.0.1"]) == 2


def test_api_sprint_matches_file_import(tmp_path: Path):
    out = tmp_path / "out"
    result = run(RunRequest(FILE_CASE / "team.yaml", FILE_CASE / "raw", out))
    assert result.code == 0, result.message
    server = make_server(out, "card", "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        sprint = json.loads(_get(f"http://127.0.0.1:{port}/api/sprint"))
        team = json.loads(_get(f"http://127.0.0.1:{port}/api/team"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
    assert sprint["asOf"] == "2026-09-10T16:00:00Z"
    assert team["asOf"] == sprint["asOf"]
    rows = {item["key"]: item for item in sprint["sprint"]["issues"]}
    assert rows["E-1"]["closedBeforeDue"] is True
    assert rows["N-1"]["closedBeforeDue"] is False
    assert rows["D-1"]["storyPoints"] == 8
    assert rows["R-1"]["scope"] == "removed"
    assert "SUB-1" not in rows
    burndown = next(item for item in sprint["sprint"]["metrics"] if item["id"] == "burndown")
    assert burndown["params"]["storyPointsAtAdd"] == 8


def test_api_sprint_matches_gold_due_rows(tmp_path: Path):
    source = M1 / "due-midnight"
    out = tmp_path / "out"
    result = run(RunRequest(source / "team.yaml", source / "canonical.json", out))
    assert result.code == 0, result.message
    server = make_server(out, "card", "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        sprint = json.loads(_get(f"http://127.0.0.1:{port}/api/sprint"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
    expected = {item["key"]: item for item in _expected("due-midnight")["sprint"]["issues"]}
    actual = {item["key"]: item for item in sprint["sprint"]["issues"]}
    for key, row in expected.items():
        for field, value in row.items():
            assert actual[key][field] == value


def _team_with_mode(tmp_path: Path, mode: str) -> Path:
    data = yaml.safe_load((M1 / "due-midnight" / "team.yaml").read_text())
    data["sources"]["mode"] = mode
    path = tmp_path / "team.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    return path


def _get(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        assert response.status == 200
        return response.read().decode()
