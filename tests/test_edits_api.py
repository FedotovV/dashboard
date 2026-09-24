"""Правки пишутся по схеме и не меняют байты слепка."""

import json
import shutil
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dashboard.api.serve import make_server
from dashboard.orchestrator.build import BuildRequest, build

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures" / "m1" / "edits-intact"


def test_second_build_keeps_the_epic_note(tmp_path: Path):
    request, path = _built(tmp_path)
    payload = path.read_bytes()
    edits_before = request.edits_path.read_bytes()
    second = build(request)
    assert second.code == 0
    assert path.read_bytes() == payload
    assert request.edits_path.read_bytes() == edits_before
    assert "Ждём макет" in payload.decode()


def test_put_rejects_a_metric_number_and_a_stale_revision(tmp_path: Path):
    request, path = _built(tmp_path)
    before = path.read_bytes()
    edits_before = request.edits_path.read_bytes()
    server, port = _serve(path, request.edits_path)
    try:
        bad = {
            "teamId": "card",
            "revision": 2,
            "value": 99,
            "projectReleases": [],
            "projectNotes": [],
        }
        assert _status(port, bad) == 422
        stale = json.loads(edits_before)
        stale["revision"] = 9
        assert _status(port, stale) == 409
        assert _status(port, None, path="/api/sprint") == 405
    finally:
        server.shutdown()
        server.thread.join(timeout=5)
    assert path.read_bytes() == before
    assert request.edits_path.read_bytes() == edits_before


def test_put_shows_the_new_note_without_rewriting_the_snapshot(tmp_path: Path):
    request, path = _built(tmp_path)
    before = path.read_bytes()
    server, port = _serve(path, request.edits_path)
    try:
        document = json.loads(request.edits_path.read_text(encoding="utf-8"))
        document["revision"] = 2
        document["projectNotes"][0]["text"] = "Новая заметка"
        body = _put(port, document)
        assert body["revision"] == 2
        page = _get(f"http://127.0.0.1:{port}/period")
        assert "Новая заметка" in page
        assert "<button" not in page
        escaped = _put(
            port,
            {
                "teamId": "card",
                "revision": 3,
                "projectReleases": document["projectReleases"],
                "projectNotes": [
                    {
                        "epicId": "P-1",
                        "text": "<script>alert(1)</script>",
                        "author": "pm",
                        "at": "2026-09-10T09:00:00Z",
                    }
                ],
            },
        )
        assert escaped["revision"] == 3
        page = _get(f"http://127.0.0.1:{port}/period")
        assert "<script>" not in page
        assert "&lt;script&gt;" in page
    finally:
        server.shutdown()
        server.thread.join(timeout=5)
    assert path.read_bytes() == before
    assert "Ждём макет" in before.decode()
    later = build(request)
    assert later.code == 4
    assert path.read_bytes() == before
    assert "Новая заметка" not in path.read_text(encoding="utf-8")


def test_form_posts_a_note_and_unknown_epic_stays_visible(tmp_path: Path):
    request, path = _built(tmp_path)
    before = path.read_bytes()
    server, port = _serve(path, request.edits_path)
    try:
        page = _post(
            port,
            {"epicId": "NO-1", "text": "чужая пометка", "author": "pm"},
        )
        assert "Чужой эпик NO-1" in page
        saved = json.loads(request.edits_path.read_text(encoding="utf-8"))
        assert any(item["text"] == "чужая пометка" for item in saved["projectNotes"])
        assert path.read_bytes() == before
    finally:
        server.shutdown()
        server.thread.join(timeout=5)


def test_put_without_an_edits_file_is_404(tmp_path: Path):
    _request, path = _built(tmp_path)
    server, port = _serve(path, None)
    try:
        assert _status(port, {"teamId": "card", "revision": 1, "projectReleases": [], "projectNotes": []}) == 404
    finally:
        server.shutdown()
        server.thread.join(timeout=5)


def _built(tmp_path: Path):
    edits = tmp_path / "edits.json"
    shutil.copy(SOURCE / "edits.json", edits)
    out = tmp_path / "out"
    request = BuildRequest(
        team_path=SOURCE / "team.yaml",
        bundle_path=SOURCE / "canonical.json",
        out_dir=out,
        edits_path=edits,
    )
    result = build(request)
    assert result.code == 0, result.message
    return request, result.path


def _serve(path: Path, edits: Path | None):
    server = make_server(path.parent.parent, "card", "127.0.0.1", 0, edits_path=edits)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.thread = thread  # type: ignore[attr-defined]
    return server, server.server_address[1]


def _put(port: int, document: dict) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/edits",
        data=json.dumps(document).encode(),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def _status(port: int, document: dict | None, path: str = "/api/edits") -> int:
    payload = b"{}" if document is None else json.dumps(document).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=payload,
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request)
    except urllib.error.HTTPError as exc:
        return exc.code
    return 200


def _post(port: int, fields: dict) -> str:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/edits",
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode()


def _get(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode()
