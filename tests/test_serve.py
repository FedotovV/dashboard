"""Serve читает слепок на 127.0.0.1 и не переписывает его."""

import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from dashboard.api.__main__ import main
from dashboard.api.serve import ServeError, make_server, require_localhost
from tests.sprint_support import build_case


def test_date_flag_selects_that_file_when_the_query_is_empty(tmp_path: Path):
    path = build_case("no-points", tmp_path)
    earlier = path.parent / "2026-09-01.json"
    earlier.write_text(path.read_text().replace("2026-09-09T16:00:00Z", "2026-09-01T16:00:00Z"), encoding="utf-8")
    server = make_server(path.parent.parent, "card", "127.0.0.1", 0, "2026-09-01")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        body = _get(f"http://127.0.0.1:{port}/api/sprint")
    finally:
        server.shutdown()
        thread.join(timeout=5)
    assert "2026-09-01T16:00:00Z" in body


def test_external_host_is_refused(tmp_path: Path):
    with pytest.raises(ServeError):
        require_localhost("0.0.0.0")
    code = main(["--snapshots", str(tmp_path), "--team", "card", "--host", "0.0.0.0", "--port", "8765"])
    assert code == 2


def test_serve_reads_twice_without_touching_bytes(tmp_path: Path):
    path = build_case("scope-days", tmp_path, history=True)
    before = path.read_bytes()
    server = make_server(path.parent.parent, "card", "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        first = _get(f"http://127.0.0.1:{port}/")
        second = _get(f"http://127.0.0.1:{port}/")
        metric = _get(f"http://127.0.0.1:{port}/api/metrics/cycleTime")
        hours = _get(f"http://127.0.0.1:{port}/api/metrics/statusHours")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/metrics/riskScore")
            raise AssertionError("чужая метрика открылась")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        request = urllib.request.Request(f"http://127.0.0.1:{port}/api/sprint", method="PUT", data=b"{}")
        try:
            urllib.request.urlopen(request)
            raise AssertionError("запись принята")
        except urllib.error.HTTPError as exc:
            assert exc.code == 405
    finally:
        server.shutdown()
        thread.join(timeout=5)
    assert first == second
    assert "utilization" not in first.lower()
    assert "утилизац" not in first.lower()
    assert "riskScore" not in first
    assert "<button" not in first
    assert "value" not in metric
    assert "value" not in hours
    assert path.read_bytes() == before


def _get(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode()
