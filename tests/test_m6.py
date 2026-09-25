"""M6: мастер пишет тот же team.yaml и не трогает слепок."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from dashboard.api.serve import make_server
from dashboard.config.hash import rule_hash
from dashboard.config.load import load_team
from dashboard.setup.store import apply_form, read_document, write_document
from tests.sprint_support import build_case

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "schema" / "examples" / "team.example.yaml"
TOKEN = "super-secret-value"


def test_put_renames_the_team_and_leaves_the_snapshot(tmp_path: Path):
    path, manifest, before_manifest, snapshot, before_snapshot = _laid_out(tmp_path)
    original_hash = rule_hash(load_team(path))
    server, port = _serve(tmp_path, path, manifest)
    try:
        page = _get(port, "/setup")
        assert "Платёжная карта" in page
        assert "JIRA_TOKEN" in page
        assert TOKEN not in page
        assert "Записать team.yaml" in page
        assert "не запускается" in page
        payload = _get_json(port, "/api/setup")
        assert payload["needsAcceptRecompute"] is False
        assert payload["manifestState"] == "same"
        assert TOKEN not in json.dumps(payload)
        document = payload["document"]
        document["team"]["name"] = "Новая карта"
        saved = _put_json(port, document)
        assert saved["needsAcceptRecompute"] is False
        assert saved["ruleHash"] == original_hash
        assert saved["document"]["team"]["name"] == "Новая карта"
    finally:
        _stop(server)
    assert load_team(path).team_name == "Новая карта"
    assert manifest.read_bytes() == before_manifest
    assert snapshot.read_bytes() == before_snapshot


def test_taxonomy_change_marks_recompute_without_writing_manifest(tmp_path: Path):
    path, manifest, before_manifest, snapshot, before_snapshot = _laid_out(tmp_path)
    server, port = _serve(tmp_path, path, manifest)
    try:
        document = _get_json(port, "/api/setup")["document"]
        document["taxonomy"]["epics"]["project"] = ["CARD-99"]
        saved = _put_json(port, document)
        assert saved["needsAcceptRecompute"] is True
        assert saved["manifestState"] == "diff"
        again = _get_json(port, "/api/setup")
        assert again["needsAcceptRecompute"] is True
    finally:
        _stop(server)
    assert manifest.read_bytes() == before_manifest
    assert snapshot.read_bytes() == before_snapshot
    assert load_team(path).taxonomy.epics.project == ("CARD-99",)


def test_rejected_writes_keep_the_file(tmp_path: Path):
    path = _copy_example(tmp_path)
    before = path.read_bytes()
    server, port = _serve(tmp_path, path, None)
    secret = "JIRA_TOKEN"
    previous = os.environ.get(secret)
    os.environ[secret] = TOKEN
    try:
        document = _get_json(port, "/api/setup")["document"]
        cases = [
            _with(document, lambda item: item.update({"catalogVersion": 2})),
            _with(document, lambda item: item["metrics"]["cycleTime"].update({"version": 2})),
            _with(document, lambda item: item["team"].update({"id": "other"})),
            _with(document, lambda item: item["taxonomy"].update({"linkTypes": ["Blocks"]})),
            _with(document, lambda item: item["calendar"].update({"hoursPerDay": 7})),
            _with(document, lambda item: item["taxonomy"]["epics"]["tech"].append("CARD-10")),
            _with(document, lambda item: item.update({"ui": {"hide": ["insights"]}})),
            _with(document, lambda item: item["sources"]["jira"].update({"baseUrl": f"https://user:{TOKEN}@jira.example.com"})),
            _with(document, lambda item: item["team"].update({"pm": TOKEN})),
            _with(document, lambda item: item["team"].update({"pm": f"lead {TOKEN} extra"})),
            _with(document, lambda item: item["sources"].update({"confluence": {"token": "abc"}})),
            _with(document, _live_without_sprint),
            _with(document, lambda item: item["sources"]["jira"].update({"deployment": "cloud"})),
        ]
        for body in cases:
            status, payload = _put_status(port, body)
            assert status == 422, payload
            assert TOKEN not in json.dumps(payload)
        status, _ = _put_status(port, {"version": 1})
        assert status == 422
        missing = _status(port, "/setup", None)
        assert missing == 200
    finally:
        if previous is None:
            os.environ.pop(secret, None)
        else:
            os.environ[secret] = previous
        _stop(server)
    assert path.read_bytes() == before


def test_form_round_trip_keeps_the_rule_hash(tmp_path: Path):
    path = _copy_example(tmp_path)
    original = rule_hash(load_team(path))
    server, port = _serve(tmp_path, path, None)
    try:
        page = _get(port, "/setup")
        fields = _form_fields(page)
        assert any(name == "team.name" and value == "Платёжная карта" for name, value in fields)
        saved = _post_form(port, fields)
        assert "team.yaml записан" in saved
        assert "Платёжная карта" in saved
        renamed = [(name, "Новая карта" if name == "team.name" else value) for name, value in fields]
        page = _post_form(port, renamed)
        assert "Новая карта" in page
    finally:
        _stop(server)
    assert load_team(path).team_name == "Новая карта"
    assert rule_hash(load_team(path)) == original
    first = path.read_bytes()
    write_document(path, read_document(path), "payments-card", None, {})
    assert path.read_bytes() == first


def test_form_remove_keeps_other_sections(tmp_path: Path):
    path = _copy_example(tmp_path)
    document = read_document(path)
    document["links"] = {"howto": "https://example.com/how"}
    changed = apply_form(
        document,
        {
            "team.name": "Новая",
            "member.0.remove": "1",
            "member.0.id": "ivanov",
            "member.0.name": "Иванов Иван",
            "member.0.kind": "member",
            "member.1.id": "petrova",
            "member.1.name": "Петрова Анна",
            "member.1.kind": "member",
        },
    )
    assert changed["links"]["howto"] == "https://example.com/how"
    assert [person["id"] for person in changed["team"]["members"]] == ["petrova"]
    written = write_document(path, changed, "payments-card", None, {})
    assert written["needsAcceptRecompute"] is False
    assert "https://example.com/how" in path.read_text(encoding="utf-8")


def test_setup_is_absent_until_config_is_connected(tmp_path: Path):
    snapshot = build_case("due-midnight", tmp_path)
    before = snapshot.read_bytes()
    server = make_server(snapshot.parent.parent, "card", "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        assert _status(port, "/setup", None) == 404
        assert _status(port, "/api/setup", None) == 404
        sprint = _get(port, "/")
    finally:
        _stop(server, thread)
    assert "<button" not in sprint
    assert snapshot.read_bytes() == before


def test_sprint_screen_stays_free_of_a_rebuild_button(tmp_path: Path):
    snapshot = build_case("due-midnight", tmp_path)
    config = tmp_path / "team.yaml"
    shutil.copy(ROOT / "fixtures" / "m1" / "due-midnight" / "team.yaml", config)
    before = snapshot.read_bytes()
    server = make_server(snapshot.parent.parent, "card", "127.0.0.1", 0, config_path=config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        sprint = _get(port, "/")
        setup = _get(port, "/setup")
        assert _status(port, "/api/sprint", b"{}") == 405
    finally:
        _stop(server, thread)
    assert "<button" not in sprint
    assert "Карта" in setup
    assert "Записать team.yaml" in setup
    assert snapshot.read_bytes() == before
    assert config.read_bytes() == (ROOT / "fixtures" / "m1" / "due-midnight" / "team.yaml").read_bytes()


def test_broken_manifest_does_not_open_the_form(tmp_path: Path):
    path = _copy_example(tmp_path)
    before = path.read_bytes()
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{", encoding="utf-8")
    server, port = _serve(tmp_path, path, manifest)
    try:
        status, payload = _put_status(port, read_document(path))
        assert status == 422
        assert "manifest" in payload["error"]
        assert _status(port, "/setup", None) == 422
    finally:
        _stop(server)
    assert path.read_bytes() == before
    assert manifest.read_text(encoding="utf-8") == "{"


def _live_without_sprint(item: dict) -> None:
    item["sources"]["mode"] = "live"
    item["sources"]["jira"]["sprintId"] = ""


def test_serve_help_mentions_config():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-m", "dashboard", "serve", "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--config" in result.stdout
    assert "--manifest" in result.stdout


def _laid_out(tmp_path: Path):
    path = _copy_example(tmp_path)
    current = rule_hash(load_team(path))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "teamId": "payments-card",
                "ruleHash": current,
                "catalogVersion": 1,
                "timings": [
                    {
                        "issueId": "card-1",
                        "terminal": True,
                        "formulaVersion": 1,
                        "ruleHash": current,
                        "changelogComplete": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    snapshot = tmp_path / "snapshots" / "payments-card" / "2026-09-01.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b'{"keep":true}\n')
    return path, manifest, manifest.read_bytes(), snapshot, snapshot.read_bytes()


def _copy_example(tmp_path: Path) -> Path:
    path = tmp_path / "team.yaml"
    shutil.copy(EXAMPLE, path)
    return path


def _serve(tmp_path: Path, config: Path, manifest: Path | None):
    server = make_server(
        tmp_path / "snapshots",
        "payments-card",
        "127.0.0.1",
        0,
        config_path=config,
        manifest_path=manifest,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.thread = thread
    return server, server.server_address[1]


def _stop(server, thread=None) -> None:
    server.shutdown()
    (thread or server.thread).join(timeout=5)


def _get(port: int, path: str) -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as response:
        return response.read().decode()


def _get_json(port: int, path: str) -> dict:
    return json.loads(_get(port, path))


def _put_json(port: int, document: dict) -> dict:
    status, payload = _put_status(port, document)
    assert status == 200, payload
    return payload


def _put_status(port: int, document: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/setup",
        data=json.dumps(document).encode(),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _post_form(port: int, fields: list[tuple[str, str]]) -> str:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/setup",
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode()


def _status(port: int, path: str, body: bytes | None) -> int:
    method = "GET" if body is None else "PUT"
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _with(document: dict, mutate) -> dict:
    copy = json.loads(json.dumps(document))
    mutate(copy)
    return copy


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: list[tuple[str, str]] = []
        self._select: str | None = None
        self._selected = False
        self._first: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        data = dict(attrs)
        if tag == "input" and data.get("type") != "checkbox" and data.get("name"):
            self.fields.append((data["name"], data.get("value", "")))
        elif tag == "select" and data.get("name"):
            self._select = data["name"]
            self._selected = False
            self._first = None
        elif tag == "option" and self._select is not None:
            value = data.get("value", "")
            if self._first is None:
                self._first = value
            if "selected" in data:
                self.fields.append((self._select, value))
                self._selected = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "select" and self._select is not None:
            if not self._selected:
                self.fields.append((self._select, self._first or ""))
            self._select = None


def _form_fields(page: str) -> list[tuple[str, str]]:
    parser = _FormParser()
    parser.feed(page)
    return parser.fields
