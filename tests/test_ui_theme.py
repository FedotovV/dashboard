"""Оболочка React хранит светлую и тёмную тему одной сетки."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_shell_keeps_both_themes():
    css = (FRONTEND / "src" / "styles.css").read_text(encoding="utf-8")
    app = (FRONTEND / "src" / "App.jsx").read_text(encoding="utf-8")
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert '[data-theme="light"]' in css
    assert '[data-theme="dark"]' in css
    assert "--brass" in css
    assert "Светлая" in app
    assert "Тёмная" in app
    assert "dashboard-theme" in html
    assert "prefers-color-scheme: dark" in html
