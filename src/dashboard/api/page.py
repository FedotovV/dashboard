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
PERSON_STATS = (
    ("total", "Всего задач"),
    ("backlog", "Бэклог"),
    ("inProgress", "В работе"),
    ("paused", "Пауза"),
    ("testing", "Тестируются"),
    ("done", "Завершены"),
    ("canceled", "Отменены"),
)
ATTENTION_ROLES = {"hold", "canceled"}
ATTENTION_SCOPE = {"added", "removed"}
MIX = (
    ("backlog", "mix-backlog"),
    ("inProgress", "mix-progress"),
    ("testing", "mix-testing"),
    ("paused", "mix-paused"),
    ("done", "mix-done"),
    ("canceled", "mix-canceled"),
    ("unknown", "mix-unknown"),
)


def render_sprint(view: dict) -> str:
    body = "\n".join(
        [
            _nav("sprint"),
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
    return _shell(body, "Спринт")


def _shell(body: str, title: str) -> str:
    shell = SHELL.read_text()
    style = STYLE.read_text()
    return (
        shell.replace("/*STYLE*/", style)
        .replace("<!--CONTENT-->", body)
        .replace("<title>Спринт</title>", f"<title>{title}</title>")
    )


def _nav(current: str) -> str:
    sprint = ' aria-current="page"' if current == "sprint" else ""
    period = ' aria-current="page"' if current == "period" else ""
    setup = ' aria-current="page"' if current == "setup" else ""
    extra = f'<a href="/setup"{setup}>Настройка</a>' if current == "setup" else ""
    return f'<nav><a href="/"{sprint}>Спринт</a><a href="/period"{period}>Период</a>{extra}</nav>'


def _header(view: dict) -> str:
    sprint = view["sprint"]
    return f"""
<header>
  <p class="kicker">Спринт</p>
  <h1>{_esc(sprint.get("id"))}</h1>
  <p>{_esc(sprint.get("start"))} — {_esc(sprint.get("end"))}</p>
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
            f"<h2>{label}</h2>{_figure(number, _positive(number) and key in ATTENTION_SCOPE)}</article>"
        )
    done_line = _completion_line(completion, incomplete)
    return f"""
<section data-widget="scope">
  <h2>Состав</h2>
  {_hint("«На старте» — задачи, которые уже были в спринте в день старта. «Добавлены» и «Сняты» — движение после старта, они выделены. Завершение считает сделанное среди стартового состава. Отменённые остаются в знаменателе и долю не увеличивают.")}
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
        number = by_role.get(role)
        attention = role in ATTENTION_ROLES and _positive(number)
        cards.append(
            f'<article class="card" data-role="{role}"><span class="key">{role}</span>'
            f"<h2>{ROLE_LABELS[role]}</h2>{_figure(number, attention)}</article>"
        )
    return (
        '<section data-widget="flow"><h2>Поток</h2>'
        + _hint(
            "Каждая задача текущего состава сидит в одной роли. Пауза и отмена выделены: с них начинается разбор. Очередь — ещё не взяли, ожидание — ревью или тест, сделано — закрыто как выполненное."
        )
        + f'<div class="roles">{"".join(cards)}</div></section>'
    )


def _timing(view: dict) -> str:
    return f"""
<section data-widget="timing">
  <h2>Цикл и ожидание</h2>
  {_hint("Число — медиана рабочих дней среди закрытых задач. Цикл считает время в работе, ожидание — время в ревью или тесте. Раскройте список: у каждой задачи секунды из слепка и понятная причина, если она в медиану не вошла. Заход короче минимального пребывания отбрасывается. Если задачу закрыли и открыли снова, считаются оба захода до текущего закрытия.")}
  <div class="grid">
    {_timing_card(view, "cycleTime", "Цикл", "в работе")}
    {_timing_card(view, "waitTime", "Ожидание", "в ожидании")}
  </div>
</section>
"""


def _timing_card(view: dict, metric_id: str, title: str, role_words: str) -> str:
    metric = _metric(view, metric_id) or {}
    explain = metric.get("explain") or ""
    per_issue = (metric.get("detail") or {}).get("perIssue") or []
    seen = {item.get("issueKey") for item in per_issue}
    rows = []
    for item in per_issue:
        seconds = item.get("seconds")
        rows.append(
            "<li"
            + (f' data-seconds="{int(seconds)}"' if isinstance(seconds, int) else "")
            + ">"
            + _issue_link(view, item.get("issueKey"))
            + f" вошла в медиану: {_duration(seconds)} {role_words}. "
            "Очередь и короткие заходы в это число не входят.</li>"
        )
    for key in metric.get("population") or []:
        if key not in seen:
            rows.append(f"<li>{_issue_link(view, key)} есть в составе медианы.</li>")
    excluded = []
    for item in metric.get("excluded") or []:
        reason = item.get("reason")
        label = REASON_LABELS.get(reason, reason)
        excluded.append(
            f'<li data-attention="true">{_issue_link(view, item.get("issueKey"))} '
            f"не вошла в медиану: {_esc(label)}. "
            "Такой заход не двигает число, чтобы случайный переход статуса не выглядел как работа.</li>"
        )
    value = metric.get("value")
    return f"""
<article class="card" data-metric="{metric_id}">
  <h2>{title}</h2>
  {_figure(value, False)}
  <p class="note">{_esc(explain)}</p>
  <p class="key">Что вошло в число</p>
  <ul>{''.join(rows) or '<li>в сумму никто не вошёл</li>'}</ul>
  <ul data-excluded="true">{''.join(excluded)}</ul>
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
        items.append(
            f'<li data-attention="true">{_issue_link(view, item.get("issueKey"))}: {_esc(label)}</li>'
        )
    body = "".join(items) or "<li>Плашек нет</li>"
    count = metric.get("value")
    return (
        '<section data-widget="hygiene"><h2>Качество данных</h2>'
        '<p class="footnote">Это не оценка команды. Плашка значит, что у задачи не хватает поля, '
        "без которого соседние числа врут: нет story points, нет исполнителя у работы в процессе, "
        "нет срока, высокий приоритет всё ещё в очереди или задача старше порога. "
        "Откройте ключ, заполните поле в задаче и дождитесь следующего слепка: плашка уйдёт. "
        "Просроченный срок сюда не входит, он в блокерах.</p>"
        + _hint("Смотрите на выделенные ключи. Ноль плашек — поля, которые просит каталог, на месте.")
        + _figure(count, _positive(count))
        + f"<ul>{body}</ul></section>"
    )


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
            f'<li data-reason="{_esc(token)}" data-attention="true">'
            f'{_issue_link(view, item.get("issueKey"))}: {labels}</li>'
        )
    body = "".join(items) or "<li>Список пуст</li>"
    return (
        '<section data-widget="blockers"><h2>Блокеры</h2>'
        + _hint(
            "Список причин, не балл. Сверху просроченный срок, затем пауза, затем работа без исполнителя. Ключ открывает задачу в Jira."
        )
        + _figure(metric.get("value"), _positive(metric.get("value")))
        + f"<ol>{body}</ol></section>"
    )


def _people(view: dict) -> str:
    metric = _metric(view, "personLoad")
    if metric is None:
        return ""
    rows = [_person(view, row) for row in (metric.get("detail") or {}).get("rows") or []]
    return (
        '<section data-widget="people"><h2>Команда</h2>'
        + _hint(
            "Под фамилией — задачи этого человека в текущем спринте. Бэклог — очередь, в работе — уже взято, пауза — блок или ожидание решения, тестируются — ревью, завершены — закрыто как сделанное. SP — сумма текущих story points, пустая оценка в сумму не входит. Полоска повторяет эти же счётчики. Человек без открытых задач остаётся в составе."
        )
        + f'<div class="people">{"".join(rows)}</div></section>'
    )


def _person(view: dict, row: dict) -> str:
    surname, rest = _name_parts(row)
    subtitle = " · ".join(part for part in (rest, row.get("personId")) if part)
    if "total" not in row:
        keys = row.get("openKeys") or []
        shown = _key_column(view, keys) if keys else "<p>нет открытых</p>"
        return (
            f'<article class="person" data-person="{_esc(row.get("personId"))}">'
            f"<h3>{_esc(surname)}</h3><p>{shown}</p></article>"
        )
    stats = []
    for key, label in PERSON_STATS:
        number = row.get(key)
        attention = key in {"paused", "canceled"} and _positive(number)
        stats.append(
            f'<div data-stat="{key}"><dt>{label}</dt><dd{_attention(attention)}>{_num(number)}</dd></div>'
        )
    stats.append(
        f'<div data-stat="storyPoints"><dt>Story points</dt><dd>{_num(row.get("storyPoints"))}</dd></div>'
    )
    stats.append(
        f'<div data-stat="openStoryPoints"><dt>Открытые SP</dt><dd>{_num(row.get("openStoryPoints"))}</dd></div>'
    )
    if _positive(row.get("pointsMissing")):
        stats.append(
            '<div data-stat="pointsMissing"><dt>Без оценки</dt>'
            f'<dd data-attention="true">{_num(row.get("pointsMissing"))}</dd></div>'
        )
    tasks = _person_tasks(view, row)
    idle = "" if row.get("openKeys") else "<p>нет открытых</p>"
    return (
        f'<article class="person" data-person="{_esc(row.get("personId"))}">'
        f"<h3>{_esc(surname)}</h3>"
        f'<p class="who">{_esc(subtitle)}</p>'
        f'<dl class="stats">{"".join(stats)}</dl>'
        f"{_mix(row)}{tasks}{idle}</article>"
    )


def _person_tasks(view: dict, row: dict) -> str:
    issues = row.get("issues") or []
    if not issues:
        return _key_column(view, row.get("openKeys") or [])
    items = []
    for issue in issues:
        points = issue.get("storyPoints")
        point_label = "" if points is None else f" · {_num(points)} SP"
        role = issue.get("role")
        items.append(
            "<li"
            + (' data-attention="true"' if role == "hold" else "")
            + ">"
            + _issue_link(view, issue.get("key"))
            + f' <span class="task-name">{_esc(issue.get("summary"))}</span>'
            + f' <span class="task-meta">{_esc(issue.get("status"))}{point_label}</span></li>'
        )
    return f'<ol class="tasks">{"".join(items)}</ol>'


def _key_column(view: dict, keys: list) -> str:
    if not keys:
        return ""
    items = "".join(f"<li>{_issue_link(view, key)}</li>" for key in keys)
    return f'<ol class="tasks">{items}</ol>'


def _mix(row: dict) -> str:
    total = row.get("total") or 0
    if not isinstance(total, (int, float)) or isinstance(total, bool) or total <= 0:
        return ""
    parts = []
    for key, css in MIX:
        count = row.get(key) or 0
        if not isinstance(count, (int, float)) or isinstance(count, bool) or count <= 0:
            continue
        width = count / total * 100
        parts.append(f'<span class="{css}" style="width:{width:.4f}%"></span>')
    if not parts:
        return ""
    return f'<div class="mix" aria-hidden="true">{"".join(parts)}</div>'


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
    behind = _behind(points)
    return f"""
<section data-widget="burndown">
  <h2>Burndown</h2>
  {_hint("Ось Y — story points на момент входа в спринт. Ось X — рабочие дни спринта: суббота, воскресенье и официальные праздники в расчёт и на график не попадают. Пунктир — ровное сгорание по этим дням. Сплошная линия — факт. Если факт выше пунктира, остаток выделен: работа сгорает медленнее плана.")}
  <p class="axes">Y — количество SP. X — рабочие дни спринта.</p>
  <p class="note">Остаток {_figure_inline(metric.get("value"), behind)}</p>
  {_spark_svg(points)}
  <table>
    <thead><tr><th>Рабочий день</th><th>Идеал, SP</th><th>Факт, SP</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _behind(points: list[dict]) -> bool:
    if not points:
        return False
    last = points[-1]
    actual = last.get("actual")
    ideal = last.get("ideal")
    if not isinstance(actual, (int, float)) or not isinstance(ideal, (int, float)):
        return False
    if isinstance(actual, bool) or isinstance(ideal, bool):
        return False
    return actual > ideal


def _spark_svg(points: list[dict]) -> str:
    if len(points) < 2:
        return ""
    actuals = [point.get("actual") for point in points if isinstance(point.get("actual"), (int, float))]
    ideals = [point.get("ideal") for point in points if isinstance(point.get("ideal"), (int, float))]
    top = max([*actuals, *ideals, 1])
    width = 440
    height = 180
    left, right, top_pad, bottom = 44, 16, 18, 32
    plot_w = width - left - right
    plot_h = height - top_pad - bottom

    def polyline(key: str) -> str:
        coords = []
        for index, point in enumerate(points):
            value = point.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            x = left if len(points) == 1 else left + index * plot_w / (len(points) - 1)
            y = top_pad + plot_h - (value / top) * plot_h
            coords.append(f"{x:.1f},{y:.1f}")
        return " ".join(coords)

    y_zero = top_pad + plot_h
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Burndown: ось Y story points, ось X рабочие дни спринта">'
        f'<text x="8" y="14" class="axis">SP</text>'
        f'<text x="{left}" y="{height - 8}" class="axis">дни спринта</text>'
        f'<line x1="{left}" y1="{top_pad}" x2="{left}" y2="{y_zero}" stroke="#7a7368"/>'
        f'<line x1="{left}" y1="{y_zero}" x2="{width - right}" y2="{y_zero}" stroke="#7a7368"/>'
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
  {_hint("Точка появляется только в день, когда слепок уже записан, и добавляется сегодня. Пустые дни между слепками не дорисовываются. Бейдж — последний слепок прошлого спринта, если он есть.")}
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
        reasons = issue.get("blockerReasons") or []
        reason_text = ", ".join(_esc(REASON_LABELS.get(reason, reason)) for reason in reasons)
        due = issue.get("dueDate") or ""
        if issue.get("closedBeforeDue") is True:
            due = f"{due} раньше срока".strip()
        reason_cell = f'<td{_attention(bool(reasons))}>{reason_text}</td>'
        due_cell = f'<td{_attention("overdue" in reasons)}>{_esc(due)}</td>'
        cells = [
            _issue_link(view, issue.get("key")),
            _esc(issue.get("summary")),
            _esc(issue.get("status")),
            _esc(issue.get("assigneeId")),
            _esc(issue.get("scope")),
        ]
        row = "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + reason_cell + due_cell
        if show_points:
            points = issue.get("storyPoints")
            row += f'<td{_attention(points is None)}>{_num(points)}</td>'
        rows.append(row + "</tr>")
    return (
        f'<section data-widget="issues"><h2>Задачи</h2>'
        + _hint("Ключ открывает задачу в Jira. Выделены срок, если он просрочен, причина блокера и пустая оценка.")
        + f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></section>"
    )


def _name_parts(row: dict) -> tuple[str, str]:
    name = row.get("name") or row.get("personId") or ""
    text = str(name).strip()
    if row.get("name") and " " in text:
        surname, rest = text.split(" ", 1)
        return surname, rest
    return text, ""


def _issue_link(view: dict, key) -> str:
    label = _esc(key)
    href = _browse_href(view, key)
    if href is None:
        return label
    return f'<a href="{_esc(href)}">{label}</a>'


def _browse_href(view: dict, key) -> str | None:
    base = view.get("jiraBaseUrl")
    if not isinstance(base, str) or not key:
        return None
    cleaned = base.strip().rstrip("/")
    if not (cleaned.startswith("https://") or cleaned.startswith("http://")):
        return None
    return f"{cleaned}/browse/{key}"


def _figure(value, attention: bool) -> str:
    return f'<span class="num"{_attention(attention)}>{_num(value)}</span>'


def _figure_inline(value, attention: bool) -> str:
    return f'<span{_attention(attention)}>{_num(value)}</span>'


def _attention(flag: bool) -> str:
    return ' data-attention="true"' if flag else ""


def _positive(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _metric(view: dict, metric_id: str) -> dict | None:
    for metric in view["sprint"].get("metrics") or []:
        if metric.get("id") == metric_id:
            return metric
    return None


def _duration(seconds) -> str:
    if not isinstance(seconds, int):
        return f"{_num(seconds)} с"
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    parts = []
    if hours:
        parts.append(f"{hours} ч")
    if minutes:
        parts.append(f"{minutes} мин")
    if not parts:
        parts.append("0 мин")
    return f"{' '.join(parts)} ({seconds} с)"


def _num(value) -> str:
    if value is None or isinstance(value, bool):
        return "—"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return json.dumps(value)
    return _esc(value)


def _esc(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _hint(text: str) -> str:
    return f'<details class="hint"><summary>Как читать</summary><p>{_esc(text)}</p></details>'
