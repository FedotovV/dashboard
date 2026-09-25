"""M7: нелокальный bind пускает запись только с токеном. Compose секрет не хранит."""

from __future__ import annotations

import json
import os
import shutil
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from dashboard.api.__main__ import main as serve_main
from dashboard.api.serve import ServeError, browser_write_allowed, make_server, require_bind
from tests.sprint_support import build_case

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "write-token-7f3a"
HOST = "127.0.0.2"


def test_nonlocal_without_a_token_does_not_listen(tmp_path: Path):
    with pytest_raises_serve():
        require_bind("0.0.0.0", None)
    assert require_bind("0.0.0.0", TOKEN) == TOKEN
    assert require_bind("127.0.0.1", TOKEN) is None
    code = serve_main(["--snapshots", str(tmp_path), "--team", "card", "--host", "10.1.1.1", "--port", "8765"])
    assert code == 2
    os.environ["DASHBOARD_TOKEN"] = "   "
    try:
        blank = serve_main(
            [
                "--snapshots",
                str(tmp_path),
                "--team",
                "card",
                "--host",
                "10.1.1.1",
                "--token-env",
                "DASHBOARD_TOKEN",
            ]
        )
    finally:
        os.environ.pop("DASHBOARD_TOKEN", None)
    assert blank == 2


def test_write_without_the_token_keeps_the_files(tmp_path: Path):
    config, edits, snapshot = _files(tmp_path)
    before_config = config.read_bytes()
    before_edits = edits.read_bytes()
    before_snapshot = snapshot.read_bytes()
    server, port = _serve(snapshot, config, edits, TOKEN)
    try:
        sprint = _get(port, "/")
        period = _get(port, "/period")
        setup = _get(port, "/setup")
        assert "<button" not in sprint
        assert "type=\"password\"" in period
        assert "type=\"password\"" in setup
        assert TOKEN not in period
        assert TOKEN not in setup
        assert _open(port, "/api/sprint", method="GET").status == 200
        missing = _put(port, _edits_body(2), None)
        assert missing.status == 401
        assert TOKEN not in missing.text
        assert "нужен токен записи" in missing.text
        query = _put(port, _edits_body(2), None, path="/api/edits?token=" + TOKEN)
        assert query.status == 401
        basic = _put(port, _edits_body(2), f"Basic {TOKEN}")
        assert basic.status == 401
        assert TOKEN not in basic.text
        wrong = _put(port, _edits_body(2), "Bearer other-token")
        assert wrong.status == 401
        setup_denied = _put(port, _setup_body(config), None, path="/api/setup")
        assert setup_denied.status == 401
    finally:
        _stop(server)
    assert config.read_bytes() == before_config
    assert edits.read_bytes() == before_edits
    assert snapshot.read_bytes() == before_snapshot


def test_bearer_and_form_token_write_without_storing_the_secret(tmp_path: Path):
    config, edits, snapshot = _files(tmp_path)
    before_snapshot = snapshot.read_bytes()
    server, port = _serve(snapshot, config, edits, TOKEN)
    try:
        saved = _put(port, _edits_body(2), f"Bearer {TOKEN}")
        assert saved.status == 200
        assert TOKEN not in saved.text
        form = urllib.parse.urlencode(
            {"epicId": "P-1", "text": "заметка", "author": "pm", "token": TOKEN}
        ).encode()
        posted = _request(port, "/api/edits", form, None, "POST")
        assert posted.status == 200
        renamed = _setup_body(config)
        renamed["team"]["name"] = "Карта плюс"
        updated = _put(port, renamed, f"Bearer {TOKEN}", path="/api/setup")
        assert updated.status == 200
        assert updated.payload["document"]["team"]["name"] == "Карта плюс"
        assert TOKEN not in updated.text
    finally:
        _stop(server)
    stored = edits.read_text(encoding="utf-8")
    assert "заметка" in stored
    assert TOKEN not in stored
    assert TOKEN not in config.read_text(encoding="utf-8")
    assert snapshot.read_bytes() == before_snapshot


def test_browser_write_allows_the_same_host_and_rejects_another_site():
    assert browser_write_allowed(None, None, "127.0.0.1:8765", "127.0.0.1") is True
    assert browser_write_allowed("http://127.0.0.1:8765", "same-origin", "127.0.0.1:8765", "127.0.0.1") is True
    assert browser_write_allowed("http://localhost:8765", "same-origin", "localhost:8765", "127.0.0.1") is True
    assert browser_write_allowed("https://evil.example", None, "127.0.0.1:8765", "127.0.0.1") is False
    assert browser_write_allowed("null", None, "127.0.0.1:8765", "127.0.0.1") is False
    assert browser_write_allowed(None, "cross-site", "127.0.0.1:8765", "127.0.0.1") is False
    assert browser_write_allowed(None, None, "evil.example", "127.0.0.1") is False
    assert browser_write_allowed("http://127.0.0.1:9", None, "127.0.0.1:8765", "127.0.0.1") is False
    assert browser_write_allowed("http://10.1.1.1:8765", "same-origin", "10.1.1.1:8765", "0.0.0.0") is True
    assert browser_write_allowed("https://evil.example", None, "10.1.1.1:8765", "0.0.0.0") is False


def test_cross_site_write_keeps_the_files(tmp_path: Path):
    config, edits, snapshot = _files(tmp_path)
    before_config = config.read_bytes()
    server = make_server(
        snapshot.parent.parent,
        "card",
        "127.0.0.1",
        0,
        edits_path=edits,
        config_path=config,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    form = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        assert "card" in _get_host(port, "/api/sprint", "127.0.0.1")
        evil = _request_host(
            port,
            "/api/edits",
            urllib.parse.urlencode({"epicId": "P-1", "text": "чужая", "author": "pm"}).encode(),
            "127.0.0.1",
            "POST",
            {**form, "Origin": "https://evil.example"},
        )
        assert evil.status == 403
        assert "Запись с другого сайта не принимается." in evil.text
        fetch = _request_host(
            port,
            "/api/setup",
            urllib.parse.urlencode({"jira.baseUrl": "https://evil.example"}).encode(),
            "127.0.0.1",
            "POST",
            {**form, "Sec-Fetch-Site": "cross-site"},
        )
        assert fetch.status == 403
        rebound = _request_host(
            port,
            "/api/edits",
            json.dumps(_edits_body(2)).encode(),
            "127.0.0.1",
            "PUT",
            {"Content-Type": "application/json", "Host": "evil.example"},
        )
        assert rebound.status == 403
        same = _request_host(
            port,
            "/api/edits",
            urllib.parse.urlencode({"epicId": "P-1", "text": "своя", "author": "pm"}).encode(),
            "127.0.0.1",
            "POST",
            {**form, "Origin": f"http://127.0.0.1:{port}"},
        )
        assert same.status == 200
    finally:
        _stop(server, thread)
    stored = edits.read_text(encoding="utf-8")
    assert "своя" in stored
    assert "чужая" not in stored
    assert config.read_bytes() == before_config


def test_localhost_write_stays_open_when_a_token_exists(tmp_path: Path):
    config, edits, snapshot = _files(tmp_path)
    server = make_server(
        snapshot.parent.parent,
        "card",
        "127.0.0.1",
        0,
        edits_path=edits,
        config_path=config,
        write_token=TOKEN,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        page = _get_host(port, "/setup", "127.0.0.1")
        saved = _put_host(port, _edits_body(2), "127.0.0.1")
    finally:
        _stop(server, thread)
    assert "type=\"password\"" not in page
    assert TOKEN not in page
    assert saved.status == 200


def test_compose_file_keeps_the_token_outside():
    text = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    service = data["services"]["dashboard"]
    command = service["command"]
    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert command[command.index("--token-env") + 1] == "DASHBOARD_TOKEN"
    assert service["ports"] == ["127.0.0.1:8765:8765"]
    assert service["environment"]["DASHBOARD_TOKEN"].startswith("${DASHBOARD_TOKEN")
    assert service["environment"]["JIRA_TOKEN"].startswith("${JIRA_TOKEN")
    assert ":ro" in service["volumes"][0]
    assert "Bearer " not in text
    assert TOKEN not in text
    assert ".env" in (ROOT / ".dockerignore").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "DASHBOARD_TOKEN" not in dockerfile
    assert "JIRA_TOKEN=" not in dockerfile
    assert "USER dashboard" in dockerfile
    assert "useradd" in dockerfile


def _files(tmp_path: Path):
    snapshot = build_case("due-midnight", tmp_path)
    config = tmp_path / "team.yaml"
    shutil.copy(ROOT / "fixtures" / "m1" / "due-midnight" / "team.yaml", config)
    edits = tmp_path / "edits.json"
    edits.write_text(
        json.dumps(
            {"teamId": "card", "revision": 1, "projectReleases": [], "projectNotes": []},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return config, edits, snapshot


def _serve(snapshot: Path, config: Path, edits: Path, token: str):
    server = make_server(
        snapshot.parent.parent,
        "card",
        HOST,
        0,
        edits_path=edits,
        config_path=config,
        write_token=token,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.thread = thread
    return server, server.server_address[1]


def _stop(server, thread=None) -> None:
    server.shutdown()
    (thread or server.thread).join(timeout=5)


def _edits_body(revision: int) -> dict:
    return {"teamId": "card", "revision": revision, "projectReleases": [], "projectNotes": []}


def _setup_body(config: Path) -> dict:
    import yaml as yaml_lib

    return json.loads(json.dumps(yaml_lib.safe_load(config.read_text(encoding="utf-8")), default=str))


def _get(port: int, path: str) -> str:
    return _get_host(port, path, HOST)


def _get_host(port: int, path: str, host: str) -> str:
    with urllib.request.urlopen(f"http://{host}:{port}{path}") as response:
        return response.read().decode()


def _put(port: int, document: dict, authorization: str | None, path: str = "/api/edits"):
    return _request(port, path, json.dumps(document).encode(), authorization, "PUT", "application/json")


def _put_host(port: int, document: dict, host: str):
    request = urllib.request.Request(
        f"http://{host}:{port}/api/edits",
        data=json.dumps(document).encode(),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    return _read(request)


def _request(port: int, path: str, body: bytes, authorization: str | None, method: str, content_type: str | None = None):
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if authorization:
        headers["Authorization"] = authorization
    request = urllib.request.Request(f"http://{HOST}:{port}{path}", data=body, method=method, headers=headers)
    return _read(request)


def _request_host(port: int, path: str, body: bytes, host: str, method: str, headers: dict[str, str]):
    request = urllib.request.Request(f"http://{host}:{port}{path}", data=body, method=method, headers=headers)
    return _read(request)


def _open(port: int, path: str, method: str):
    request = urllib.request.Request(f"http://{HOST}:{port}{path}", method=method)
    return _read(request)


def _read(request: urllib.request.Request):
    try:
        with urllib.request.urlopen(request) as response:
            text = response.read().decode()
            return _Response(response.status, text)
    except urllib.error.HTTPError as exc:
        return _Response(exc.code, exc.read().decode())


class _Response:
    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self.text = text

    @property
    def payload(self) -> dict:
        return json.loads(self.text)


def pytest_raises_serve():
    import pytest

    return pytest.raises(ServeError)
