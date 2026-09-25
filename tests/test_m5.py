"""M5: записанный ответ Server и fileimport дают одни метрики. Сеть наружу не ходим."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

import pytest
import yaml

from dashboard.connectors import CollectError, collect_bundle
from dashboard.connectors.http import urllib_transport
from dashboard.orchestrator.build import BuildRequest, build
from dashboard.orchestrator.run import RunRequest, run
from dashboard.api.serve import make_server

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "fixtures" / "m4" / "file-sprint" / "raw"
FILE_TEAM = ROOT / "fixtures" / "m4" / "file-sprint" / "team.yaml"
LIVE_TEAM = ROOT / "fixtures" / "m5" / "server" / "team.yaml"
DUE = ROOT / "fixtures" / "m1" / "due-midnight"
TOKEN = "super-secret-token"
CLOCK = datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc)
ENV = {"JIRA_TOKEN": TOKEN}


def test_recorded_api_matches_file_import_bundle(tmp_path: Path):
    live = collect_bundle(
        "live",
        Path("live"),
        _sources(),
        transport=_recorded(),
        now=CLOCK,
        environ=ENV,
    )
    file_bundle = collect_bundle("file", RAW, _sources())
    for key in ("asOf", "issues", "statusChanges", "memberships", "sprints", "links"):
        assert live[key] == file_bundle[key], key
    assert live["bundleId"] == "live-s"
    assert live["sourceWatermark"].startswith("live:")
    assert live["sourceWatermark"] != file_bundle["sourceWatermark"]
    assert TOKEN not in json.dumps(live)


def test_api_sprint_matches_file_import(tmp_path: Path):
    live_out = tmp_path / "live"
    file_out = tmp_path / "file"
    manifest = tmp_path / "manifest.json"
    live = run(
        RunRequest(
            LIVE_TEAM,
            Path("live"),
            live_out,
            manifest_path=manifest,
            transport=_recorded(),
            now=CLOCK,
            environ=ENV,
        )
    )
    file_result = run(RunRequest(FILE_TEAM, RAW, file_out))
    assert live.code == 0, live.message
    assert file_result.code == 0, file_result.message
    live_doc = json.loads(live.path.read_text())
    file_doc = json.loads(file_result.path.read_text())
    assert live_doc["sprint"]["issues"] == file_doc["sprint"]["issues"]
    assert _burndown(live_doc) == _burndown(file_doc) == 8
    assert TOKEN not in live.path.read_text()
    server = make_server(live_out, "card", "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        sprint = json.loads(_get(f"http://127.0.0.1:{port}/api/sprint"))
        team = json.loads(_get(f"http://127.0.0.1:{port}/api/team"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
    rows = {item["key"]: item for item in sprint["sprint"]["issues"]}
    assert rows["E-1"]["closedBeforeDue"] is True
    assert rows["N-1"]["closedBeforeDue"] is False
    assert rows["D-1"]["storyPoints"] == 8
    assert rows["R-1"]["scope"] == "removed"
    assert "SUB-1" not in rows
    assert _burndown(sprint) == 8
    assert team["asOf"] == "2026-09-10T16:00:00Z"
    assert TOKEN not in json.dumps(sprint)


def test_manifest_seals_terminal_and_second_run_keeps_bytes(tmp_path: Path):
    out = tmp_path / "out"
    manifest = tmp_path / "manifest.json"
    request = RunRequest(
        LIVE_TEAM,
        Path("live"),
        out,
        manifest_path=manifest,
        transport=_recorded(),
        now=CLOCK,
        environ=ENV,
    )
    first = run(request)
    assert first.code == 0, first.message
    payload = first.path.read_bytes()
    sealed = json.loads(manifest.read_text())
    ids = [row["issueId"] for row in sealed["timings"]]
    assert ids == ["d-1", "e-1", "n-1"]
    assert all(row["terminal"] is True and row["changelogComplete"] is True for row in sealed["timings"])
    assert all(set(row) == {"changelogComplete", "formulaVersion", "issueId", "ruleHash", "terminal"} for row in sealed["timings"])
    assert "seconds" not in manifest.read_text()
    assert TOKEN not in manifest.read_text()
    before = manifest.read_bytes()
    document = json.loads(before)
    document["timings"].append(
        {
            "changelogComplete": True,
            "formulaVersion": 1,
            "issueId": "c-1",
            "ruleHash": document["ruleHash"],
            "terminal": True,
        }
    )
    document["timings"].append(
        {
            "changelogComplete": True,
            "formulaVersion": 1,
            "issueId": "ghost",
            "ruleHash": document["ruleHash"],
            "terminal": True,
        }
    )
    manifest.write_text(json.dumps(document))
    second = run(request)
    assert second.code == 0
    assert first.path.read_bytes() == payload
    assert manifest.read_bytes() == before
    assert [row["issueId"] for row in json.loads(manifest.read_text())["timings"]] == ids


def test_sparse_history_is_not_changelog_complete(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    result = build(
        BuildRequest(
            team_path=DUE / "team.yaml",
            bundle_path=DUE / "canonical.json",
            out_dir=tmp_path / "out",
            manifest_path=manifest,
        )
    )
    assert result.code == 0, result.message
    rows = {item["issueId"]: item for item in json.loads(manifest.read_text())["timings"]}
    assert rows["e-1"]["changelogComplete"] is False
    assert rows["n-1"]["terminal"] is True


def test_cloud_live_does_not_call_transport():
    def transport(_url, _headers):
        raise AssertionError("сеть открылась")

    with pytest.raises(CollectError, match="Server"):
        collect_bundle(
            "live",
            Path("live"),
            {"jira": {"deployment": "cloud", "baseUrl": "https://jira.example.com", "sprintId": "1", "authEnv": "JIRA_TOKEN"}},
            transport=transport,
            environ=ENV,
        )


def test_missing_token_does_not_call_transport():
    def transport(_url, _headers):
        raise AssertionError("сеть открылась")

    with pytest.raises(CollectError, match="токен"):
        collect_bundle("live", Path("live"), _sources(), transport=transport, environ={})


def test_foreign_redirect_stops(tmp_path: Path):
    calls = []

    def transport(url, _headers):
        calls.append(url)
        return SimpleNamespace(status=302, body=TOKEN.encode(), headers={"location": "https://evil.example/steal"})

    with pytest.raises(CollectError, match="редирект") as caught:
        collect_bundle("live", Path("live"), _sources(), transport=transport, now=CLOCK, environ=ENV)
    assert calls
    assert all(urlsplit(url).hostname == "jira.example.com" for url in calls)
    assert TOKEN not in str(caught.value)


def test_error_status_hides_the_body():
    def transport(_url, _headers):
        return SimpleNamespace(status=500, body=TOKEN.encode(), headers={})

    with pytest.raises(CollectError, match="500") as caught:
        collect_bundle("live", Path("live"), _sources(), transport=transport, now=CLOCK, environ=ENV)
    assert TOKEN not in str(caught.value)


def test_search_reads_every_page():
    def issue(issue_id: str) -> dict:
        return {
            "id": issue_id,
            "key": issue_id.upper(),
            "fields": {
                "summary": issue_id,
                "issuetype": {"name": "Story", "subtask": False},
                "project": {"key": "CARD"},
                "status": {"name": "In Progress"},
                "assignee": {"name": "dev"},
                "created": "2026-09-07T07:00:00Z",
                "labels": [],
            },
        }

    pages = {"0": [issue("a-1")], "1": [issue("b-1")]}
    asked = []

    def transport(url, _headers):
        if "/sprint/" in url:
            body = {
                "id": "s",
                "name": "Спринт",
                "state": "active",
                "startDate": "2026-09-07",
                "endDate": "2026-09-18",
            }
        elif "/changelog" in url:
            body = {"histories": [], "total": 0}
        else:
            start = parse_qs(urlsplit(url).query).get("startAt", ["0"])[0]
            asked.append(start)
            body = {"issues": pages[start], "total": 2}
        return SimpleNamespace(status=200, body=json.dumps(body).encode(), headers={})

    bundle = collect_bundle("live", Path("live"), _sources(), transport=transport, now=CLOCK, environ=ENV)
    assert asked == ["0", "1"]
    assert [item["id"] for item in bundle["issues"]] == ["a-1", "b-1"]


def test_localhost_transport_sends_bearer_and_keeps_the_token(tmp_path: Path):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            seen.append(self.headers.get("Authorization"))
            if self.path.startswith("/rest/agile/1.0/sprint/"):
                body = {
                    "id": "s",
                    "name": "Спринт",
                    "state": "active",
                    "startDate": "2026-09-07",
                    "endDate": "2026-09-18",
                }
            elif self.path.startswith("/rest/api/2/search"):
                body = {
                    "issues": [
                        {
                            "id": "e-1",
                            "key": "E-1",
                            "fields": {
                                "summary": "Живая",
                                "issuetype": {"name": "Story", "subtask": False},
                                "project": {"key": "CARD"},
                                "status": {"name": "In Progress"},
                                "assignee": {"name": "dev"},
                                "created": "2026-09-07T10:00:00.000+0300",
                                "labels": [],
                            },
                        }
                    ],
                    "total": 1,
                }
            else:
                body = {"histories": [], "total": 0}
            raw = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    team = tmp_path / "team.yaml"
    data = yaml.safe_load(LIVE_TEAM.read_text())
    data["sources"]["jira"]["baseUrl"] = f"http://127.0.0.1:{port}"
    team.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    try:
        result_bundle = collect_bundle(
            "live",
            Path("live"),
            data["sources"],
            transport=urllib_transport,
            now=CLOCK,
            environ=ENV,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
    assert seen
    assert set(seen) == {f"Bearer {TOKEN}"}
    assert result_bundle["issues"][0]["key"] == "E-1"
    assert TOKEN not in json.dumps(result_bundle)
    assert team.exists()


def test_image_does_not_carry_a_token():
    text = (ROOT / "Dockerfile").read_text()
    assert "python:3.11-slim" in text
    assert "schema" in text
    assert "Bearer" not in text
    assert "JIRA_TOKEN" not in text
    assert ".env" not in text
    ignore = (ROOT / ".dockerignore").read_text()
    assert ".git" in ignore


def _sources() -> dict:
    return yaml.safe_load(LIVE_TEAM.read_text())["sources"]


def _recorded():
    search = json.loads((RAW / "search.json").read_text())
    changelogs = json.loads((RAW / "changelogs.json").read_text())
    sprints = json.loads((RAW / "sprints.json").read_text())

    def transport(url, headers):
        assert headers["Authorization"] == f"Bearer {TOKEN}"
        if "/rest/agile/1.0/sprint/" in url:
            body = sprints[0]
        elif "/changelog" in url:
            issue_id = url.split("/issue/")[1].split("/changelog")[0]
            histories = (changelogs.get(issue_id) or {}).get("histories") or []
            body = {"histories": histories, "total": len(histories)}
        elif "/rest/api/2/search" in url:
            body = {"issues": search["issues"], "total": len(search["issues"])}
        else:
            return SimpleNamespace(status=404, body=b"", headers={})
        return SimpleNamespace(status=200, body=json.dumps(body).encode(), headers={})

    return transport


def _burndown(document: dict) -> int:
    sprint = document.get("sprint") or document
    metrics = sprint["metrics"] if "metrics" in sprint else sprint["sprint"]["metrics"]
    return next(item["params"]["storyPointsAtAdd"] for item in metrics if item["id"] == "burndown")


def _get(url: str) -> str:
    with urlopen(url) as response:
        assert response.status == 200
        return response.read().decode()
