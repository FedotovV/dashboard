"""HTML экрана «Период». Числа копируются из документа маршрута."""

from __future__ import annotations

import math

from dashboard.api.page import (
    _attention,
    _duration,
    _esc,
    _hint,
    _issue_link,
    _nav,
    _num,
    _shell,
)

CATEGORIES = {
    "project": "проект",
    "tech": "техника",
    "other": "другое",
    "unknown": "не разобрано",
}


def render_period(view: dict) -> str:
    body = "\n".join(
        [
            _nav("period"),
            _header(view),
            _coverage(view),
            _unknown(view),
            _hours(view),
            _people(view),
            _epics(view),
            _completion(view),
            '<p class="foot">Числа метрик взяты из слепка. Релиз и заметка читаются из файла правок, если он подключён. Сборка с этого экрана не запускается.</p>',
        ]
    )
    return _shell(body, "Период")


def _header(view: dict) -> str:
    period = view.get("period") or {}
    return f"""
<header>
  <p class="kicker">Период</p>
  <h1>{_esc(period.get("id"))}</h1>
  <p>{_esc(period.get("start"))} — {_esc(period.get("end"))}</p>
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
    return f'<div class="banner" data-widget="coverage" data-attention="true">{items}</div>'


def _unknown(view: dict) -> str:
    metric = _period_metric(view, "classification")
    if metric is None or not _unknown_raised(metric):
        return ""
    threshold = (metric.get("params") or {}).get("unknownWarnPct")
    return (
        '<div class="banner" data-widget="unknown" data-attention="true">'
        f"<p>Не разобрано {_num(metric.get('value'))}% при пороге {_num(threshold)}%.</p>"
        "<p>Плашка стоит над часами в статусе. Это покрытие классификации, не оценка команды. "
        "Путь каждой такой задачи — в списке людей, отметка «нет головы».</p>"
        "</div>"
    )


def _unknown_raised(metric: dict) -> bool:
    if "unknown-above-threshold" in (metric.get("warnings") or []):
        return True
    value = metric.get("value")
    threshold = (metric.get("params") or {}).get("unknownWarnPct")
    if isinstance(value, bool) or isinstance(threshold, bool):
        return False
    if not isinstance(value, (int, float)) or not isinstance(threshold, (int, float)):
        return False
    return value > threshold


def _hours(view: dict) -> str:
    metric = _period_metric(view, "statusHours") or {}
    detail = metric.get("detail") or {}
    timing = (view.get("coverage") or {}).get("timing")
    days = detail.get("days") or []
    hidden = timing == "none" or (metric.get("value") is None and not days)
    hint = _hint(
        "Кольцо делит уже посчитанные секунды на две части: начатые в этом периоде и пришедшие из прошлого. "
        "Доля к ёмкости и параллельность — диагностика, на экране два знака. Цвета нормы нет, целью эти числа не являются. "
        "Строка дня показывает секунды одного человека до масштаба и после."
    )
    if hidden:
        shown = (
            f"<p>Ряд скрыт: coverage.timing = {_esc(timing)}. "
            "Нулевая шкала не рисуется.</p>"
        )
    else:
        inherited = _seconds(detail.get("inheritedSeconds"))
        own = _seconds(detail.get("ownSeconds"))
        shown = f"""
<div class="hours">
  {_ring(inherited, own)}
  <div>
    <p>Пришли из прошлого {_marked_duration(inherited)}</p>
    <p>Начаты в этом периоде {_duration(own)}</p>
    <p data-diagnostic="parallelism">Параллельность {_ratio(detail.get("parallelism"))}</p>
    <p data-diagnostic="ratio">Доля к ёмкости {_ratio(metric.get("value"))}</p>
    <p class="legend"><span><i class="swatch swatch-own"></i>свои</span><span><i class="swatch swatch-inherited"></i>из прошлого</span></p>
  </div>
</div>
<details>
  <summary>Секунды по людям и дням</summary>
  <ul>
  {''.join(_day(row) for row in days)}
  </ul>
</details>
"""
    explain = metric.get("explain") or ""
    note = f'<p class="note">{_esc(explain)}</p>' if explain else ""
    return f"""
<section data-widget="hours">
  <h2>Часы в статусе</h2>
  <p>Часы в статусе, не списание.</p>
  {hint}
  {shown}
  {note}
</section>
"""


def _marked_duration(seconds: int) -> str:
    text = _duration(seconds)
    if seconds > 0:
        return f'<span data-attention="true">{text}</span>'
    return text


def _day(row: dict) -> str:
    outside = bool(row.get("outside"))
    label = " вне состава" if outside else ""
    return (
        f"<li{_attention(outside)}>"
        f"{_esc(row.get('personId'))} {_esc(row.get('date'))}{label}: "
        f"до масштаба {_num(row.get('rawSeconds'))} с, после {_num(row.get('scaledSeconds'))} с"
        "</li>"
    )


def _ring(inherited: int, own: int) -> str:
    total = inherited + own
    if total <= 0:
        return ""
    radius = 42
    circle = 2 * math.pi * radius
    own_len = circle * own / total
    inherited_len = circle * inherited / total
    turn = f' transform="rotate(-90 60 60)"'
    return (
        '<svg class="ring" viewBox="0 0 120 120" role="img" '
        'aria-label="Кольцо часов: свои и пришедшие из прошлого">'
        f'<circle cx="60" cy="60" r="{radius}" fill="none" stroke="#e4ddd0" stroke-width="14"/>'
        f'<circle cx="60" cy="60" r="{radius}" fill="none" stroke="#1c2430" stroke-width="14" '
        f'stroke-dasharray="{own_len:.2f} {circle:.2f}" stroke-dashoffset="0"{turn}/>'
        f'<circle cx="60" cy="60" r="{radius}" fill="none" stroke="#8a6a3b" stroke-width="14" '
        f'stroke-dasharray="{inherited_len:.2f} {circle:.2f}" stroke-dashoffset="{-own_len:.2f}"{turn}/>'
        "</svg>"
    )


def _people(view: dict) -> str:
    metric = _period_metric(view, "classification") or {}
    paths = ((metric.get("detail") or {}).get("paths")) or []
    issues = {item.get("key"): item for item in view.get("issues") or []}
    roster = {}
    order = []
    for row in (((view.get("people") or {}).get("detail") or {}).get("rows")) or []:
        roster[row.get("personId")] = row
        order.append(row.get("personId"))
    groups: dict = {}
    for path in paths:
        issue = issues.get(path.get("issueKey")) or {}
        groups.setdefault(issue.get("assigneeId"), []).append(path)
    person_ids = [person_id for person_id in order if person_id in groups]
    person_ids.extend(person_id for person_id in groups if person_id not in person_ids)
    cards = []
    for person_id in person_ids:
        row = roster.get(person_id) or {}
        if person_id:
            title = row.get("name") or person_id
        else:
            title = "Без исполнителя"
        items = []
        for path in groups[person_id]:
            unknown = path.get("reason") == "unknown" or path.get("category") == "unknown"
            items.append(
                f"<li{_attention(unknown)}>{_issue_link(view, path.get('issueKey'))} "
                f'<span class="path">{_esc(_path_text(path))}</span></li>'
            )
        cards.append(
            f'<article class="person"><h3>{_esc(title)}</h3><ul class="tasks">{"".join(items)}</ul></article>'
        )
    return f"""
<section data-widget="people">
  <h2>Люди</h2>
  {_hint("Под именем — ключи периода и путь классификации из слепка: голова эпика, правило, явная метка или «нет головы». Дерево на экране заново не обходится. Выделено то, что осталось без головы.")}
  <div class="people">{''.join(cards)}</div>
</section>
"""


def _path_text(path: dict) -> str:
    reason = path.get("reason")
    category = CATEGORIES.get(path.get("category"), path.get("category") or "")
    if reason == "head" and path.get("headId"):
        return f"голова {path.get('headId')}, {category}"
    if reason == "rule":
        return f"правило, {category}"
    if reason == "label":
        subtype = path.get("subtype") or ""
        return f"метка {subtype}, {category}".strip()
    return "нет головы"


def _epics(view: dict) -> str:
    metric = _period_metric(view, "projectList") or {}
    warnings = metric.get("warnings") or []
    rows = ((metric.get("detail") or {}).get("rows")) or []
    notices = []
    for warning in warnings:
        text = str(warning)
        if text == "no-epics":
            notices.append("Список эпиков пуст. Пустая таблица не рисуется.")
        elif text == "edits-team-mismatch":
            notices.append("Файл правок другой команды. Пометки не подставлены.")
        elif text.startswith("unknown-epic:"):
            notices.append(f"Чужой эпик {text.split(':', 1)[1]} в правках. Запись не скрыта.")
    banner = ""
    if notices:
        items = "".join(f"<p>{_esc(item)}</p>" for item in notices)
        banner = f'<div class="banner" data-widget="epic-warnings">{items}</div>'
    names = {
        item.get("personId"): item.get("name")
        for item in (((view.get("people") or {}).get("detail") or {}).get("rows")) or []
        if item.get("name")
    }
    table = ""
    if rows and "no-epics" not in warnings:
        body = []
        for row in rows:
            note = row.get("note")
            marked = bool(note)
            body.append(
                "<tr>"
                f"<td>{_issue_link(view, row.get('key'))}</td>"
                f"<td>{_esc(row.get('name'))}</td>"
                f"<td>{_num(row.get('status'))}</td>"
                f"<td>{_num(names.get(row.get('featureLead'), row.get('featureLead')))}</td>"
                f"<td>{_num(row.get('release'))}</td>"
                f"<td{_attention(marked)}>{_num(note)}</td>"
                "</tr>"
            )
        table = (
            "<table><thead><tr><th>Ключ</th><th>Название</th><th>Статус</th>"
            "<th>Feature lead</th><th>Релиз</th><th>Заметка</th></tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table>"
        )
    form = ""
    if view.get("editsEnabled"):
        form = """
<form class="edits" method="post" action="/api/edits">
  <label>Эпик <input name="epicId" required></label>
  <label>Релиз <input name="release"></label>
  <label>Заметка <textarea name="text" rows="3"></textarea></label>
  <label>Автор <input name="author" required></label>
  <input type="submit" value="Сохранить пометку">
</form>
"""
    return f"""
<section data-widget="epics">
  <h2>Эпики</h2>
  {_hint("Релиз и заметка приходят из файла правок, не из Jira. Чужой ключ эпика остаётся предупреждением. Число метрики форма не меняет.")}
  {banner}
  {table}
  {form}
</section>
"""


def _completion(view: dict) -> str:
    metric = view.get("completion") or {}
    detail = metric.get("detail") or {}
    incomplete = (view.get("coverage") or {}).get("membership") == "incomplete"
    value = metric.get("value")
    if value is None or incomplete or not detail:
        figure = "<p>—</p>"
    else:
        figure = (
            f'<p><a href="/">{_num(detail.get("done"))} из {_num(detail.get("committed"))}</a></p>'
        )
    return f"""
<section data-widget="completion">
  <h2>Завершение к старту спринта</h2>
  {_hint("Это число уже лежит на экране спринта. Здесь оно не пересчитывается. Ссылка открывает тот экран.")}
  {figure}
</section>
"""


def _period_metric(view: dict, metric_id: str) -> dict | None:
    for metric in (view.get("period") or {}).get("metrics") or []:
        if metric.get("id") == metric_id:
            return metric
    return None


def _ratio(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _num(value)
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.2f}"
    return _num(value)


def _seconds(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)
