"""HTML экрана «Спринт». Числа копируются из документа маршрута."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHELL = ROOT / "web" / "sprint.html"
STYLE = ROOT / "web" / "sprint.css"

ROLES = ("active", "wait", "hold", "queue", "done", "canceled", "total")
ROLE_LABELS = {
    "active": "В работе",
    "wait": "Ожидание",
    "hold": "Пауза",
    "queue": "Очередь",
    "done": "Сделано",
    "canceled": "Отменено",
    "total": "Всего",
}
SCOPE_LABELS = {
    "committed": "На старте",
    "added": "Добавлены",
    "removed": "Сняты",
}
REASON_LABELS = {
    "overdue": "просрочено",
    "hold": "пауза",
    "no-assignee": "нет исполнителя",
    "no-story-points": "нет story points",
    "no-due-date": "нет срока",
    "high-priority-queue": "высокий приоритет в очереди",
    "too-old": "слишком старая",
    "shorter-than-min-stay": "короче минимального пребывания",
    "no-timing": "нет тайминга",
}


def render_sprint(view: dict) -> str:
    shell = SHELL.read_text()
    style = STYLE.read_text()
    body = "\n".join(
        [
            _header(view),
            _coverage(view),
            _hygiene(view),
            _scope(view),
            _flow(view),
            _timing(view),
            _blockers(view),
            _people(view),
            _burndown(view),
            _trend(view),
            _issues(view),
            '<p class="foot">Числа взяты из слепка. Сборка с этого экрана не запускается.</p>',
        ]
    )
    return shell.replace("/*STYLE*/", style).replace("<!--CONTENT-->", body)


def _header(view: dict) -> str:
    sprint = view["sprint"]
    return f"""
<header>
  <p class="kicker">Спринт</p>
  <h1>{_esc(sprint.get("id"))}</h1>
  <p>{_esc(sprint.get("start"))} — {_esc(sprint.get("end"))}</p>
  <p>asOf <time datetime="{_esc(view.get("asOf"))}">{_esc(view.get("asOf"))}</time> · {_esc(view.get("timezone"))}</p>
  <p>Команда {_esc(view.get("teamId"))}</p>
</header>
"""


def _coverage(view: dict) -> str:
    coverage = view.get("coverage") or {}
    notes = []
    timing = coverage.get("timing")
    if timing in {"none", "partial"}:
        notes.append(f"Тайминги: coverage.timing = {timing}")
    if coverage.get("membership") == "incomplete":
        notes.append("Состав: coverage.membership = incomplete")
    if not notes:
        return ""
    items = "".join(f"<p>{_esc(note)}</p>" for note in notes)
    return f'<div class="banner" data-widget="coverage">{items}</div>'


def _scope(view: dict) -> str:
    scope = _metric(view, "scopeChange")
    completion = _metric(view, "completionVsCommitted")
    detail = (scope or {}).get("detail") or {}
    incomplete = (view.get("coverage") or {}).get("membership") == "incomplete"
    cards = []
    for key, label in SCOPE_LABELS.items():
        number = None if incomplete else detail.get(key)
        cards.append(
            f'<article class="card" data-scope="{key}"><span class="key">{key}</span>'
            f"<h2>{label}</h2><span class=\"num\">{_num(number)}</span></article>"
        )
    done_line = _completion_line(completion, incomplete)
    return f"""
<section data-widget="scope">
  <h2>Состав</h2>
  <div class="grid">{''.join(cards)}</div>
  <p class="note" data-completion="true">{done_line}</p>
</section>
"""


def _completion_line(metric: dict | None, incomplete: bool) -> str:
    if metric is None or incomplete or metric.get("value") is None:
        return "Завершение к старту: состав на старте не собран"
    detail = metric.get("detail") or {}
    done = detail.get("done")
    committed = detail.get("committed")
    if done is None or committed is None:
        return "Завершение к старту: состав на старте не собран"
    return f"Завершение к старту: {int(done)} из {int(committed)}"


def _flow(view: dict) -> str:
    metric = _metric(view, "sprintFlow")
    by_role = ((metric or {}).get("detail") or {}).get("byRole") or {}
    cards = []
    for role in ROLES:
        cards.append(
            f'<article class="card" data-role="{role}"><span class="key">{role}</span>'
            f"<h2>{ROLE_LABELS[role]}</h2><span class=\"num\">{_num(by_role.get(role))}</span></article>"
        )
    return f'<section data-widget="flow"><h2>Поток</h2><div class="roles">{"".join(cards)}</div></section>'


def _timing(view: dict) -> str:
    return f"""
<section data-widget="timing">
  <h2>Цикл и ожидание</h2>
  <div class="grid">
    {_timing_card(view, "cycleTime", "Цикл")}
    {_timing_card(view, "waitTime", "Ожидание")}
  </div>
</section>
"""


def _timing_card(view: dict, metric_id: str, title: str) -> str:
    metric = _metric(view, metric_id) or {}
    explain = metric.get("explain") or ""
    rows = []
    for item in (metric.get("detail") or {}).get("perIssue") or []:
        rows.append(f"<li>{_esc(item.get('issueKey'))}: {_num(item.get('seconds'))} с</li>")
    for item in metric.get("population") or []:
        if not any(item == row.get("issueKey") for row in (metric.get("detail") or {}).get("perIssue") or []):
            rows.append(f"<li>{_esc(item)}</li>")
    excluded = []
    for item in metric.get("excluded") or []:
        reason = item.get("reason")
        label = REASON_LABELS.get(reason, reason)
        excluded.append(f"<li>{_esc(item.get('issueKey'))}: {_esc(label)}</li>")
    value = metric.get("value")
    shown = "—" if value is None else _num(value)
    return f"""
<article class="card" data-metric="{metric_id}">
  <h2>{title}</h2>
  <span class="num">{shown}</span>
  <p class="note">{_esc(explain)}</p>
  <details>
    <summary>Ключи</summary>
    <ul>{''.join(rows) or '<li>в сумму никто не вошёл</li>'}</ul>
    <ul data-excluded="true">{''.join(excluded)}</ul>
  </details>
</article>
"""


def _hygiene(view: dict) -> str:
    metric = _metric(view, "hygiene")
    if metric is None:
        return ""
    items = []
    for item in (metric.get("detail") or {}).get("items") or []:
        reason = item.get("reason")
        label = REASON_LABELS.get(reason, reason)
        items.append(f"<li>{_esc(item.get('issueKey'))}: {_esc(label)}</li>")
    body = "".join(items) or "<li>Плашек нет</li>"
    return f'<section data-widget="hygiene"><h2>Качество данных</h2><ul>{body}</ul></section>'


def _blockers(view: dict) -> str:
    metric = _metric(view, "blockers")
    if metric is None:
        return ""
    items = []
    for item in (metric.get("detail") or {}).get("items") or []:
        reasons = item.get("reasons") or []
        token = reasons[0] if reasons else ""
        labels = ", ".join(_esc(REASON_LABELS.get(reason, reason)) for reason in reasons)
        items.append(
            f'<li data-reason="{_esc(token)}">{_esc(item.get("issueKey"))}: {labels}</li>'
        )
    body = "".join(items) or "<li>Список пуст</li>"
    return f'<section data-widget="blockers"><h2>Блокеры</h2><ol>{body}</ol></section>'


def _people(view: dict) -> str:
    metric = _metric(view, "personLoad")
    if metric is None:
        return ""
    rows = []
    for row in (metric.get("detail") or {}).get("rows") or []:
        keys = row.get("openKeys") or []
        shown = ", ".join(_esc(key) for key in keys) if keys else "нет открытых"
        rows.append(
            f'<article class="person" data-person="{_esc(row.get("personId"))}">'
            f'<h2>{_esc(row.get("personId"))}</h2><p>{shown}</p></article>'
        )
    return f'<section data-widget="people"><h2>Люди</h2><div class="people">{"".join(rows)}</div></section>'


def _burndown(view: dict) -> str:
    coverage = (view.get("coverage") or {}).get("storyPoints")
    metric = _metric(view, "burndown")
    if coverage != "full" or metric is None or metric.get("value") is None:
        return ""
    points = (metric.get("detail") or {}).get("points") or []
    rows = []
    for point in points:
        rows.append(
            "<tr>"
            f"<td>{_esc(point.get('date'))}</td>"
            f"<td>{_num(point.get('ideal'))}</td>"
            f"<td>{_num(point.get('actual'))}</td>"
            "</tr>"
        )
    return f"""
<section data-widget="burndown">
  <h2>Burndown</h2>
  <p class="note">Остаток {_num(metric.get("value"))}</p>
  {_spark_svg(points)}
  <table>
    <thead><tr><th>Дата</th><th>Идеал</th><th>Факт</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _spark_svg(points: list[dict]) -> str:
    if len(points) < 2:
        return ""
    actuals = [point.get("actual") for point in points if isinstance(point.get("actual"), (int, float))]
    ideals = [point.get("ideal") for point in points if isinstance(point.get("ideal"), (int, float))]
    top = max([*actuals, *ideals, 1])
    width = 320
    height = 120

    def polyline(key: str) -> str:
        coords = []
        for index, point in enumerate(points):
            value = point.get(key)
            if not isinstance(value, (int, float)):
                continue
            x = 0 if len(points) == 1 else index * width / (len(points) - 1)
            y = height - (value / top) * height
            coords.append(f"{x:.1f},{y:.1f}")
        return " ".join(coords)

    return (
        f'<svg viewBox="0 0 {width} {height}" role="img">'
        f'<polyline fill="none" stroke="#7a7368" stroke-dasharray="4 3" points="{polyline("ideal")}"/>'
        f'<polyline fill="none" stroke="#1c2430" points="{polyline("actual")}"/>'
        "</svg>"
    )


def _trend(view: dict) -> str:
    trend = view["sprint"].get("trend") or {}
    previous = trend.get("previous")
    badge = ""
    if previous:
        by_role = previous.get("byRole") or {}
        bits = " ".join(f"{role} {_num(by_role.get(role))}" for role in ROLES)
        badge = (
            f'<p data-widget="previous">Прошлый спринт {_esc(previous.get("sprintId"))} '
            f'({_esc(previous.get("snapshotId"))}): {bits}</p>'
        )
    days = []
    for point in trend.get("sparkline") or []:
        days.append(f'<li data-date="{_esc(point.get("date"))}">{_esc(point.get("date"))}: {_num(point.get("done"))}</li>')
    return f"""
<section data-widget="trend">
  <h2>Тренд</h2>
  {badge}
  <ul>{''.join(days)}</ul>
</section>
"""


def _issues(view: dict) -> str:
    show_points = (view.get("coverage") or {}).get("storyPoints") != "off"
    head = "<th>Ключ</th><th>Название</th><th>Статус</th><th>Исполнитель</th><th>Состав</th><th>Блокеры</th><th>Срок</th>"
    if show_points:
        head += '<th data-column="storyPoints">Story points</th>'
    rows = []
    for issue in view["sprint"].get("issues") or []:
        reasons = ", ".join(_esc(REASON_LABELS.get(reason, reason)) for reason in issue.get("blockerReasons") or [])
        due = issue.get("dueDate") or ""
        if issue.get("closedBeforeDue") is True:
            due = f"{due} раньше срока".strip()
        cells = [
            _esc(issue.get("key")),
            _esc(issue.get("summary")),
            _esc(issue.get("status")),
            _esc(issue.get("assigneeId")),
            _esc(issue.get("scope")),
            reasons,
            _esc(due),
        ]
        if show_points:
            cells.append(_num(issue.get("storyPoints")))
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return (
        f'<section data-widget="issues"><h2>Задачи</h2>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></section>"
    )


def _metric(view: dict, metric_id: str) -> dict | None:
    for metric in view["sprint"].get("metrics") or []:
        if metric.get("id") == metric_id:
            return metric
    return None


def _num(value) -> str:
    if value is None or isinstance(value, bool):
        return "—"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return json.dumps(value)
    return _esc(value)


def _esc(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)
