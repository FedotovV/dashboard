"""Чтение и запись того же team.yaml. Слепок и manifest мастер не меняет."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from dashboard.config.hash import rule_hash
from dashboard.config.invariants import check_team_invariants
from dashboard.config.load import CATALOG_VERSION, METRIC_VERSIONS, ConfigError, load_team

ROOT = Path(__file__).resolve().parents[3]
TEAM_SCHEMA = ROOT / "schema" / "team.schema.json"
MANIFEST_SCHEMA = ROOT / "schema" / "manifest.schema.json"
LABEL = "team.yaml"
SECRET_KEYS = {
    "token",
    "password",
    "secret",
    "apitoken",
    "pat",
    "authorization",
    "bearer",
    "accesstoken",
    "refreshtoken",
}
AUTH_ENV = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
KEY_ORDER = {
    "": [
        "version",
        "catalogVersion",
        "team",
        "calendar",
        "period",
        "sources",
        "workflow",
        "taxonomy",
        "scope",
        "ui",
        "metrics",
        "links",
        "planning",
    ],
    "team": ["id", "name", "locale", "pm", "teamLead", "members", "alumni"],
    "calendar": [
        "timezone",
        "workdays",
        "workStart",
        "workEnd",
        "breakMinutes",
        "breakStart",
        "hoursPerDay",
        "holidays",
        "extraWorkdays",
    ],
    "sources": ["mode", "jira", "confluence", "gitlab", "messenger"],
    "jira": ["deployment", "baseUrl", "boardId", "sprintId", "authEnv", "fields"],
    "fields": ["storyPoints", "epicLink"],
    "workflow": ["usesDueDate", "statusMap"],
    "taxonomy": ["priority", "epics", "linkTypes", "rules", "otherSubtype"],
    "epics": ["project", "tech"],
    "scope": ["issueTypes", "projectKeys", "countSubtasks"],
    "metrics": ["cycleTime", "hygiene", "classification"],
}
ITEM_ORDER = {
    "statusMap": ["status", "category", "role", "outcome"],
    "members": [
        "id",
        "name",
        "jiraUsername",
        "jiraAccountId",
        "role",
        "allocation",
        "featureLeadOf",
        "activeFrom",
        "activeTo",
        "absences",
    ],
    "alumni": [
        "id",
        "name",
        "jiraUsername",
        "jiraAccountId",
        "role",
        "allocation",
        "featureLeadOf",
        "activeFrom",
        "activeTo",
        "absences",
    ],
    "rules": ["category", "when"],
    "absences": ["start", "end"],
}


class SetupError(Exception):
    def __init__(self, status: int, problems: list[str]):
        self.status = status
        self.problems = problems
        self.message = problems[0] if problems else "настройка отклонена"
        super().__init__(self.message)


def read_document(path: Path) -> dict:
    if not path.is_file():
        raise SetupError(404, ["team.yaml не найден"])
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SetupError(422, ["team.yaml не читается"]) from exc
    data = _jsonable(raw)
    if not isinstance(data, dict):
        raise SetupError(422, ["team.yaml должен быть объектом"])
    return data


def describe(path: Path, team_id: str, manifest_path: Path | None) -> dict:
    data = read_document(path)
    try:
        loaded = load_team(path)
    except ConfigError as exc:
        raise SetupError(422, [str(exc)]) from exc
    current = rule_hash(loaded)
    state, stored = _manifest_state(manifest_path, current)
    return {
        "document": data,
        "ruleHash": current,
        "manifestRuleHash": stored,
        "manifestState": state,
        "needsAcceptRecompute": state == "diff",
    }


def write_document(
    path: Path,
    data: dict,
    team_id: str,
    manifest_path: Path | None,
    environ: dict | None = None,
) -> dict:
    if not isinstance(data, dict):
        raise SetupError(422, ["тело должно быть объектом"])
    problems = collect_problems(data, team_id, environ if environ is not None else os.environ)
    if problems:
        raise SetupError(422, problems)
    if not path.parent.is_dir():
        raise SetupError(422, ["каталог team.yaml не найден"])
    text = dump_team(data)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    try:
        loaded = load_team(temporary)
        _manifest_state(manifest_path, rule_hash(loaded))
    except ConfigError as exc:
        temporary.unlink(missing_ok=True)
        raise SetupError(422, [str(exc)]) from exc
    except SetupError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    os.replace(temporary, path)
    return describe(path, team_id, manifest_path)


def apply_form(previous: dict, fields: dict[str, str]) -> dict:
    data = json.loads(json.dumps(previous))
    _overlay_scalars(data, fields)
    statuses = _statuses(fields)
    if statuses is not None:
        data.setdefault("workflow", {})["statusMap"] = statuses
    if "epics.project" in fields or "epics.tech" in fields:
        epics = data.setdefault("taxonomy", {}).setdefault("epics", {})
        if "epics.project" in fields:
            epics["project"] = _split(fields["epics.project"])
        if "epics.tech" in fields:
            epics["tech"] = _split(fields["epics.tech"])
    if "linkTypes" in fields:
        data.setdefault("taxonomy", {})["linkTypes"] = _split(fields["linkTypes"])
    rules = _rules(fields)
    if rules is not None:
        data.setdefault("taxonomy", {})["rules"] = rules
    if "other.prodLabel" in fields or "other.techLabel" in fields:
        other = dict((data.get("taxonomy") or {}).get("otherSubtype") or {})
        if "other.prodLabel" in fields:
            _put(other, "prodLabel", fields["other.prodLabel"].strip())
        if "other.techLabel" in fields:
            _put(other, "techLabel", fields["other.techLabel"].strip())
        if other:
            data.setdefault("taxonomy", {})["otherSubtype"] = other
        elif "taxonomy" in data:
            data["taxonomy"].pop("otherSubtype", None)
    people = _people(fields)
    if people is not None:
        data.setdefault("team", {})["members"] = people["members"]
        data["team"]["alumni"] = people["alumni"]
    _overlay_metrics(data, fields)
    return data


def collect_problems(data: dict, team_id: str, environ: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["тело должно быть объектом"]
    team = data.get("team") if isinstance(data.get("team"), dict) else {}
    if team.get("id") != team_id:
        problems.append("id команды не меняется мастером")
    if data.get("version") != 1:
        problems.append("version остаётся 1")
    if data.get("catalogVersion") != CATALOG_VERSION:
        problems.append(f"неизвестная catalogVersion {data.get('catalogVersion')}")
    for metric_id, body in (data.get("metrics") or {}).items():
        if not isinstance(body, dict):
            continue
        version = body.get("version", 1)
        expected = METRIC_VERSIONS.get(metric_id)
        if expected is None or version != expected:
            problems.append(f"неизвестная версия формулы {metric_id}={version}")
    _secrets(data, _secret_values(data, environ), problems, "$")
    jira = ((data.get("sources") or {}).get("jira") or {}) if isinstance(data.get("sources"), dict) else {}
    auth = jira.get("authEnv") if isinstance(jira, dict) else None
    if auth is not None and (not isinstance(auth, str) or AUTH_ENV.fullmatch(auth) is None):
        problems.append("authEnv — имя переменной, не сам секрет")
    schema = json.loads(TEAM_SCHEMA.read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    problems.extend(f"{list(item.path)}: {item.message}" for item in schema_errors)
    if schema_errors:
        return problems
    try:
        problems.extend(check_team_invariants(data, LABEL))
    except (KeyError, TypeError, ValueError):
        problems.append("team.yaml не сходится с инвариантами")
        return problems
    mode = (data.get("sources") or {}).get("mode") or "fixture"
    if mode == "live":
        if not jira.get("sprintId"):
            problems.append("для live нужен конкретный sprintId")
        if not jira.get("authEnv"):
            problems.append("для live нужно имя переменной authEnv")
        base = jira.get("baseUrl") or ""
        parsed = urlparse(base) if isinstance(base, str) else None
        if parsed is None or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            problems.append("для live нужен http(s) baseUrl")
    return problems


def dump_team(data: dict) -> str:
    return yaml.safe_dump(
        _order(data, ""),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def _manifest_state(path: Path | None, current: str) -> tuple[str, str | None]:
    if path is None:
        return "off", None
    if not path.exists():
        return "new", None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(422, ["manifest не читается"]) from exc
    schema = json.loads(MANIFEST_SCHEMA.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(raw))
    if errors:
        raise SetupError(422, ["manifest не проходит схему"])
    stored = raw["ruleHash"]
    if stored == current:
        return "same", stored
    return "diff", stored


def _secret_values(data: dict, environ: dict) -> set[str]:
    jira = ((data.get("sources") or {}).get("jira") or {}) if isinstance(data.get("sources"), dict) else {}
    auth = jira.get("authEnv") if isinstance(jira, dict) else None
    if not isinstance(auth, str):
        return set()
    value = environ.get(auth)
    if isinstance(value, str) and value != "":
        return {value}
    return set()


def _secrets(value, banned: set[str], problems: list[str], path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if _key_norm(key) in SECRET_KEYS:
                problems.append(f"{path}.{key}: секрет в YAML не пишется")
            _secrets(item, banned, problems, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _secrets(item, banned, problems, f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if any(secret in value for secret in banned):
        problems.append(f"{path}: значение переменной authEnv попало в файл")
    if "://" not in value:
        return
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        problems.append(f"{path}: в адресе не должно быть логина и секрета")
    for key in parse_qs(parsed.query):
        if _key_norm(key) in SECRET_KEYS:
            problems.append(f"{path}: секрет в адресе не пишется")


def _key_norm(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _overlay_scalars(data: dict, fields: dict[str, str]) -> None:
    team = data.setdefault("team", {})
    if "team.name" in fields:
        team["name"] = fields["team.name"].strip()
    if "team.pm" in fields:
        _put(team, "pm", fields["team.pm"].strip())
    if "team.teamLead" in fields:
        _put(team, "teamLead", fields["team.teamLead"].strip())
    calendar = data.setdefault("calendar", {})
    if "calendar.timezone" in fields:
        calendar["timezone"] = fields["calendar.timezone"].strip()
    if "calendar.workdays" in fields:
        calendar["workdays"] = [_int(part, "workdays") for part in _split(fields["calendar.workdays"])]
    if "calendar.workStart" in fields:
        calendar["workStart"] = fields["calendar.workStart"].strip()
    if "calendar.workEnd" in fields:
        calendar["workEnd"] = fields["calendar.workEnd"].strip()
    if "calendar.breakMinutes" in fields:
        calendar["breakMinutes"] = _int(fields["calendar.breakMinutes"], "breakMinutes")
    if "calendar.breakStart" in fields:
        _put(calendar, "breakStart", fields["calendar.breakStart"].strip())
    if "calendar.hoursPerDay" in fields:
        calendar["hoursPerDay"] = _number(fields["calendar.hoursPerDay"], "hoursPerDay")
    if "calendar.holidays" in fields:
        calendar["holidays"] = _split(fields["calendar.holidays"])
    if "calendar.extraWorkdays" in fields:
        calendar["extraWorkdays"] = _split(fields["calendar.extraWorkdays"])
    period = data.setdefault("period", {})
    for key, field in (("id", "period.id"), ("start", "period.start"), ("end", "period.end")):
        if field in fields:
            period[key] = fields[field].strip()
    sources = data.setdefault("sources", {})
    if "sources.mode" in fields:
        sources["mode"] = fields["sources.mode"].strip()
    jira = sources.setdefault("jira", {})
    for key, field in (
        ("deployment", "jira.deployment"),
        ("baseUrl", "jira.baseUrl"),
        ("boardId", "jira.boardId"),
        ("sprintId", "jira.sprintId"),
        ("authEnv", "jira.authEnv"),
    ):
        if field in fields:
            _put(jira, key, fields[field].strip())
    if "jira.storyPoints" in fields or "jira.epicLink" in fields:
        stored = jira.setdefault("fields", {})
        if "jira.storyPoints" in fields:
            text = fields["jira.storyPoints"].strip()
            stored["storyPoints"] = text or None
        if "jira.epicLink" in fields:
            _put(stored, "epicLink", fields["jira.epicLink"].strip())
    workflow = data.setdefault("workflow", {})
    if "workflow.usesDueDate" in fields:
        workflow["usesDueDate"] = _bool(fields["workflow.usesDueDate"])
    scope = data.setdefault("scope", {})
    if "scope.issueTypes" in fields:
        scope["issueTypes"] = _split(fields["scope.issueTypes"])
    if "scope.projectKeys" in fields:
        scope["projectKeys"] = _split(fields["scope.projectKeys"])
    if "scope.countSubtasks" in fields:
        scope["countSubtasks"] = _bool(fields["scope.countSubtasks"])
    if "taxonomy.priority" in fields:
        data.setdefault("taxonomy", {})["priority"] = _split(fields["taxonomy.priority"])


def _overlay_metrics(data: dict, fields: dict[str, str]) -> None:
    names = ("metrics.minStaySeconds", "metrics.highPriorities", "metrics.maxAgeDays", "metrics.unknownWarnPct")
    if not any(name in fields for name in names):
        return
    metrics = data.setdefault("metrics", {})
    if "metrics.minStaySeconds" in fields:
        metrics.setdefault("cycleTime", {})["minStaySeconds"] = _int(fields["metrics.minStaySeconds"], "minStaySeconds")
    if "metrics.maxAgeDays" in fields or "metrics.highPriorities" in fields:
        hygiene = metrics.setdefault("hygiene", {})
        if "metrics.maxAgeDays" in fields:
            hygiene["maxAgeDays"] = _int(fields["metrics.maxAgeDays"], "maxAgeDays")
        if "metrics.highPriorities" in fields:
            hygiene["highPriorities"] = _split(fields["metrics.highPriorities"])
    if "metrics.unknownWarnPct" in fields:
        metrics.setdefault("classification", {})["unknownWarnPct"] = _number(
            fields["metrics.unknownWarnPct"], "unknownWarnPct"
        )


def _statuses(fields: dict[str, str]) -> list[dict] | None:
    rows = _indexed(fields, "status")
    if rows is None:
        return None
    result = []
    for row in rows:
        if _removed(row) or not row.get("status", "").strip():
            continue
        item = {
            "status": row["status"].strip(),
            "category": row.get("category", "").strip(),
            "role": row.get("role", "").strip(),
        }
        outcome = row.get("outcome", "").strip()
        if outcome:
            item["outcome"] = outcome
        result.append(item)
    return result


def _rules(fields: dict[str, str]) -> list[dict] | None:
    rows = _indexed(fields, "rule")
    if rows is None:
        return None
    result = []
    for row in rows:
        if _removed(row) or not row.get("category", "").strip():
            continue
        when = {}
        label = row.get("label", "").strip()
        project_key = row.get("projectKey", "").strip()
        if label:
            when["label"] = label
        if project_key:
            when["projectKey"] = project_key
        result.append({"category": row["category"].strip(), "when": when})
    return result


def _people(fields: dict[str, str]) -> dict[str, list] | None:
    rows = _indexed(fields, "member")
    if rows is None:
        return None
    result = {"members": [], "alumni": []}
    for row in rows:
        if _removed(row) or not row.get("id", "").strip() or not row.get("name", "").strip():
            continue
        person: dict = {"id": row["id"].strip(), "name": row["name"].strip()}
        for key, source in (
            ("jiraUsername", "jiraUsername"),
            ("jiraAccountId", "jiraAccountId"),
            ("role", "role"),
            ("activeFrom", "activeFrom"),
            ("activeTo", "activeTo"),
        ):
            if source in row:
                _put(person, key, row[source].strip())
        if row.get("allocation", "").strip():
            person["allocation"] = _number(row["allocation"], "allocation")
        if "featureLeadOf" in row and row["featureLeadOf"].strip():
            person["featureLeadOf"] = _split(row["featureLeadOf"])
        absences = _absences(row)
        if absences:
            person["absences"] = absences
        kind = "alumni" if row.get("kind", "").strip() == "alumni" else "members"
        result[kind].append(person)
    return result


def _absences(row: dict[str, str]) -> list[dict]:
    groups: dict[int, dict[str, str]] = {}
    for key, value in row.items():
        match = re.fullmatch(r"absence\.(\d+)\.(start|end)", key)
        if match:
            groups.setdefault(int(match.group(1)), {})[match.group(2)] = value
    result = []
    for index in sorted(groups):
        start = groups[index].get("start", "").strip()
        end = groups[index].get("end", "").strip()
        if not start and not end:
            continue
        result.append({"start": start, "end": end})
    return result


def _indexed(fields: dict[str, str], prefix: str) -> list[dict[str, str]] | None:
    found: dict[int, dict[str, str]] = {}
    pattern = re.compile(rf"^{re.escape(prefix)}\.(\d+)\.(.+)$")
    seen = False
    for key, value in fields.items():
        match = pattern.match(key)
        if not match:
            continue
        seen = True
        found.setdefault(int(match.group(1)), {})[match.group(2)] = value
    if not seen:
        return None
    return [found[index] for index in sorted(found)]


def _removed(row: dict[str, str]) -> bool:
    return row.get("remove", "").strip().lower() in {"1", "true", "on", "yes"}


def _split(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n,]", text) if part.strip()]


def _put(target: dict, key: str, value: str) -> None:
    if value:
        target[key] = value
    else:
        target.pop(key, None)


def _bool(text: str) -> bool:
    return text.strip().lower() in {"1", "true", "yes", "on", "да"}


def _int(text: str, label: str) -> int:
    try:
        return int(text.strip())
    except (AttributeError, ValueError) as exc:
        raise SetupError(422, [f"{label} должно быть целым числом"]) from exc


def _number(text: str, label: str):
    raw = text.strip()
    try:
        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        return float(raw)
    except (AttributeError, ValueError) as exc:
        raise SetupError(422, [f"{label} должно быть числом"]) from exc


def _jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _order(value, parent: str):
    if isinstance(value, list):
        return [_order(item, parent) for item in value]
    if not isinstance(value, dict):
        return value
    preferred = ITEM_ORDER.get(parent, KEY_ORDER.get(parent, []))
    keys = [key for key in preferred if key in value] + [key for key in value if key not in preferred]
    return {key: _order(value[key], key) for key in keys}
