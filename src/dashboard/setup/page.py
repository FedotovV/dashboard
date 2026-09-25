"""HTML мастера настройки. Форма пишет тот же team.yaml и слепок не считает."""

from __future__ import annotations

from dashboard.api.page import _esc, _nav, _shell

CATEGORIES = (
    ("todo", "todo"),
    ("indeterminate", "indeterminate"),
    ("done", "done"),
)
ROLES = (
    ("queue", "queue"),
    ("active", "active"),
    ("wait", "wait"),
    ("hold", "hold"),
    ("terminal", "terminal"),
)
OUTCOMES = (
    ("", "по умолчанию"),
    ("completed", "completed"),
    ("canceled", "canceled"),
)
MODES = (("fixture", "fixture"), ("file", "file"), ("live", "live"))
DEPLOYMENTS = (("server", "server"), ("cloud", "cloud"))
BOOLS = (("true", "да"), ("false", "нет"))
KINDS = (("member", "в составе"), ("alumni", "alumni"))
RULE_CATEGORIES = (("project", "проект"), ("tech", "техника"), ("other", "другое"))


def render_setup(view: dict) -> str:
    document = view["document"]
    body = "\n".join(
        [
            _nav("setup"),
            _header(view),
            _form(document, bool(view.get("writeTokenRequired"))),
            '<p class="foot">Секрет в файл не пишется: только имя переменной authEnv. Сборка с этого экрана не запускается.</p>',
        ]
    )
    return _shell(body, "Настройка")


def render_setup_error(problems: list[str]) -> str:
    items = "".join(f"<li>{_esc(item)}</li>" for item in problems)
    body = "\n".join([_nav("setup"), "<h1>Настройка</h1>", f"<ul class=\"problems\">{items}</ul>"])
    return _shell(body, "Настройка")


def _header(view: dict) -> str:
    notes = [_state_note(view)]
    if view.get("saved"):
        notes.append("team.yaml записан. Слепок и manifest не менялись.")
    problems = "".join(f"<li>{_esc(item)}</li>" for item in view.get("problems") or [])
    problem_list = f'<ul class="problems">{problems}</ul>' if problems else ""
    lines = "".join(f"<p>{_esc(note)}</p>" for note in notes)
    return f"""
<header>
  <p class="kicker">Настройка</p>
  <h1>{_esc(view["document"]["team"]["name"])}</h1>
  {lines}
  {problem_list}
  <p>Идентификатор команды <code>{_esc(view["document"]["team"]["id"])}</code> этим экраном не меняется. Каталог формул остаётся версии {_esc(view["document"].get("catalogVersion"))}.</p>
  <p>Хеш правил складывается из календаря, статусов, эпиков, связей и состава задач. Его пишет build в manifest.</p>
</header>
"""


def _state_note(view: dict) -> str:
    state = view.get("manifestState")
    if state == "diff" or view.get("needsAcceptRecompute"):
        return "Хеш правил разошёлся с manifest. Следующий build остановится, пока не передан --accept-recompute."
    if state == "same":
        return "Хеш правил совпадает с manifest."
    if state == "new":
        return "Файл manifest ещё не создан. Его пишет build, не этот экран."
    return "Manifest не подключён. Запись меняет только team.yaml."


def _form(document: dict, write_token_required: bool = False) -> str:
    team = document["team"]
    calendar = document["calendar"]
    period = document["period"]
    sources = document.get("sources") or {}
    jira = sources.get("jira") or {}
    fields = jira.get("fields") or {}
    workflow = document["workflow"]
    taxonomy = document["taxonomy"]
    other = taxonomy.get("otherSubtype") or {}
    scope = document["scope"]
    metrics = document.get("metrics") or {}
    cycle = metrics.get("cycleTime") or {}
    hygiene = metrics.get("hygiene") or {}
    classification = metrics.get("classification") or {}
    sections = [
        _section(
            "Команда",
            [
                _input("Название", "team.name", team.get("name")),
                _input("PM", "team.pm", team.get("pm")),
                _input("Тимлид", "team.teamLead", team.get("teamLead")),
                _people(team),
            ],
        ),
        _section(
            "Календарь",
            [
                _input("Часовой пояс", "calendar.timezone", calendar.get("timezone")),
                _input("Рабочие дни", "calendar.workdays", _csv(calendar.get("workdays"))),
                _input("Начало", "calendar.workStart", calendar.get("workStart")),
                _input("Конец", "calendar.workEnd", calendar.get("workEnd")),
                _input("Перерыв, минут", "calendar.breakMinutes", calendar.get("breakMinutes", 0)),
                _input("Начало перерыва", "calendar.breakStart", calendar.get("breakStart")),
                _input("Часов в дне", "calendar.hoursPerDay", calendar.get("hoursPerDay")),
                _input("Праздники", "calendar.holidays", _csv(calendar.get("holidays"))),
                _input("Дополнительные рабочие дни", "calendar.extraWorkdays", _csv(calendar.get("extraWorkdays"))),
            ],
        ),
        _section(
            "Период",
            [
                _input("Идентификатор", "period.id", period.get("id")),
                _input("Начало", "period.start", period.get("start")),
                _input("Конец", "period.end", period.get("end")),
            ],
        ),
        _section(
            "Jira",
            [
                _select("Режим", "sources.mode", sources.get("mode") or "fixture", MODES),
                _select("Поставка", "jira.deployment", jira.get("deployment") or "server", DEPLOYMENTS),
                _input("Адрес", "jira.baseUrl", jira.get("baseUrl")),
                _input("Доска", "jira.boardId", jira.get("boardId")),
                _input("Спринт", "jira.sprintId", jira.get("sprintId")),
                _input("Имя переменной с токеном", "jira.authEnv", jira.get("authEnv")),
                _input("Поле story points", "jira.storyPoints", fields.get("storyPoints")),
                _input("Поле эпика", "jira.epicLink", fields.get("epicLink")),
            ],
        ),
        _section(
            "Статусы",
            [
                _select("Считать срок", "workflow.usesDueDate", _bool_value(workflow.get("usesDueDate")), BOOLS),
                _statuses(workflow.get("statusMap") or []),
            ],
        ),
        _section(
            "Эпики и связи",
            [
                _input("Приоритет", "taxonomy.priority", _csv(taxonomy.get("priority"))),
                _input("Эпики проекта", "epics.project", _csv((taxonomy.get("epics") or {}).get("project"))),
                _input("Эпики техники", "epics.tech", _csv((taxonomy.get("epics") or {}).get("tech"))),
                _input("Типы связей", "linkTypes", _csv(taxonomy.get("linkTypes"))),
                _input("Метка операционной работы", "other.prodLabel", other.get("prodLabel")),
                _input("Метка прочей техники", "other.techLabel", other.get("techLabel")),
                _rules(taxonomy.get("rules") or []),
            ],
        ),
        _section(
            "Состав задач",
            [
                _input("Типы", "scope.issueTypes", _csv(scope.get("issueTypes"))),
                _input("Проекты", "scope.projectKeys", _csv(scope.get("projectKeys"))),
                _select("Считать сабтаски", "scope.countSubtasks", _bool_value(scope.get("countSubtasks")), BOOLS),
            ],
        ),
        _section(
            "Параметры формул",
            [
                "<p>Версия формулы остаётся 1. Здесь только параметры каталога.</p>",
                _input("Минимальное пребывание, секунд", "metrics.minStaySeconds", cycle.get("minStaySeconds", 900)),
                _input("Высокие приоритеты", "metrics.highPriorities", _csv(hygiene.get("highPriorities"))),
                _input("Максимальный возраст, дней", "metrics.maxAgeDays", hygiene.get("maxAgeDays", 90)),
                _input("Порог unknown, %", "metrics.unknownWarnPct", classification.get("unknownWarnPct", 15)),
            ],
        ),
    ]
    return (
        '<form class="setup" method="post" action="/api/setup">'
        + "".join(sections)
        + _token_field(write_token_required)
        + '<button type="submit">Записать team.yaml</button></form>'
    )


def _token_field(required: bool) -> str:
    if not required:
        return ""
    return '<label>Токен записи <input type="password" name="token" autocomplete="off"></label>'


def _section(title: str, parts: list[str]) -> str:
    return f"<section><h2>{_esc(title)}</h2>{''.join(parts)}</section>"


def _people(team: dict) -> str:
    rows = []
    people = [("member", person) for person in team.get("members") or []]
    people += [("alumni", person) for person in team.get("alumni") or []]
    for index, (kind, person) in enumerate(people):
        rows.append(_person(index, kind, person, blank=False))
    rows.append(_person(len(people), "member", {}, blank=True))
    return "".join(rows)


def _person(index: int, kind: str, person: dict, blank: bool) -> str:
    prefix = f"member.{index}"
    absences = person.get("absences") or []
    absence_fields = []
    for absence_index, absence in enumerate(absences):
        absence_fields.append(_input("Отсутствие с", f"{prefix}.absence.{absence_index}.start", absence.get("start")))
        absence_fields.append(_input("по", f"{prefix}.absence.{absence_index}.end", absence.get("end")))
    if not blank:
        absence_fields.append(_input("Отсутствие с", f"{prefix}.absence.{len(absences)}.start", ""))
        absence_fields.append(_input("по", f"{prefix}.absence.{len(absences)}.end", ""))
    remove = ""
    if not blank:
        remove = f'<label><input type="checkbox" name="{prefix}.remove" value="1"> убрать из состава</label>'
    return (
        f'<div class="setup-row">{_select("Роль в файле", f"{prefix}.kind", kind, KINDS)}'
        f'{_input("id", f"{prefix}.id", person.get("id"))}'
        f'{_input("Имя", f"{prefix}.name", person.get("name"))}'
        f'{_input("Логин", f"{prefix}.jiraUsername", person.get("jiraUsername"))}'
        f'{_input("accountId", f"{prefix}.jiraAccountId", person.get("jiraAccountId"))}'
        f'{_input("Роль", f"{prefix}.role", person.get("role"))}'
        f'{_input("Ставка", f"{prefix}.allocation", person.get("allocation", ""))}'
        f'{_input("Ведёт эпики", f"{prefix}.featureLeadOf", _csv(person.get("featureLeadOf")))}'
        f'{_input("Активен с", f"{prefix}.activeFrom", person.get("activeFrom"))}'
        f'{_input("Активен по", f"{prefix}.activeTo", person.get("activeTo"))}'
        f'{"".join(absence_fields)}{remove}</div>'
    )


def _statuses(rows: list[dict]) -> str:
    rendered = [_status(index, row, blank=False) for index, row in enumerate(rows)]
    rendered.append(_status(len(rows), {}, blank=True))
    return "".join(rendered)


def _status(index: int, row: dict, blank: bool) -> str:
    prefix = f"status.{index}"
    remove = ""
    if not blank:
        remove = f'<label><input type="checkbox" name="{prefix}.remove" value="1"> убрать статус</label>'
    return (
        f'<div class="setup-row">{_input("Статус", f"{prefix}.status", row.get("status"))}'
        f'{_select("Категория", f"{prefix}.category", row.get("category") or "todo", CATEGORIES)}'
        f'{_select("Роль", f"{prefix}.role", row.get("role") or "queue", ROLES)}'
        f'{_select("Исход", f"{prefix}.outcome", row.get("outcome") or "", OUTCOMES)}'
        f"{remove}</div>"
    )


def _rules(rows: list[dict]) -> str:
    rendered = [_rule(index, row) for index, row in enumerate(rows)]
    rendered.append(_rule(len(rows), {}))
    return "".join(rendered)


def _rule(index: int, row: dict) -> str:
    when = row.get("when") or {}
    prefix = f"rule.{index}"
    return (
        f'<div class="setup-row">{_select("Категория правила", f"{prefix}.category", row.get("category") or "", (("", "—"), *RULE_CATEGORIES))}'
        f'{_input("Метка", f"{prefix}.label", when.get("label"))}'
        f'{_input("Ключ проекта", f"{prefix}.projectKey", when.get("projectKey"))}</div>'
    )


def _input(label: str, name: str, value) -> str:
    return (
        f'<label>{_esc(label)}<input name="{_esc(name)}" value="{_esc(_text(value))}"></label>'
    )


def _select(label: str, name: str, value, options: tuple) -> str:
    current = _text(value)
    items = []
    for item, caption in options:
        selected = " selected" if _text(item) == current else ""
        items.append(f'<option value="{_esc(item)}"{selected}>{_esc(caption)}</option>')
    return f'<label>{_esc(label)}<select name="{_esc(name)}">{"".join(items)}</select></label>'


def _csv(values) -> str:
    if not values:
        return ""
    return ", ".join(_text(item) for item in values)


def _text(value) -> str:
    if value is None:
        return ""
    return str(value)


def _bool_value(value) -> str:
    return "true" if value else "false"
