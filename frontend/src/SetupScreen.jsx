import { useEffect, useState } from "react";
import { saveSetup } from "./api.js";

const MODES = [["fixture", "fixture"], ["file", "file"], ["live", "live"]];
const DEPLOYMENTS = [["server", "server"], ["cloud", "cloud"]];
const BOOLS = [["true", "да"], ["false", "нет"]];
const KINDS = [["member", "в составе"], ["alumni", "alumni"]];
const CATEGORIES = [["todo", "todo"], ["indeterminate", "indeterminate"], ["done", "done"]];
const ROLES = [["queue", "queue"], ["active", "active"], ["wait", "wait"], ["hold", "hold"], ["terminal", "terminal"]];
const OUTCOMES = [["", "по умолчанию"], ["completed", "completed"], ["canceled", "canceled"]];
const RULE_CATEGORIES = [["", "—"], ["project", "проект"], ["tech", "техника"], ["other", "другое"]];

export function SetupScreen({ view, error, onSaved }) {
  const [draft, setDraft] = useState(() => (view?.document ? structuredClone(view.document) : null));
  const [token, setToken] = useState("");
  const [problems, setProblems] = useState(view?.problems || []);
  const [saved, setSaved] = useState(Boolean(view?.saved));

  useEffect(() => {
    if (!view?.document) {
      return;
    }
    setDraft(structuredClone(view.document));
    setProblems(view.problems || []);
    if (view.saved) {
      setSaved(true);
    }
  }, [view]);

  if (error) {
    return <p className="sub">{error}</p>;
  }
  if (!view || !draft) {
    return <p className="sub">Читаем настройку.</p>;
  }

  const team = draft.team || {};
  const calendar = draft.calendar || {};
  const period = draft.period || {};
  const sources = draft.sources || {};
  const jira = sources.jira || {};
  const fields = jira.fields || {};
  const workflow = draft.workflow || {};
  const taxonomy = draft.taxonomy || {};
  const other = taxonomy.otherSubtype || {};
  const scope = draft.scope || {};
  const metrics = draft.metrics || {};
  const cycle = metrics.cycleTime || {};
  const hygiene = metrics.hygiene || {};
  const classification = metrics.classification || {};

  function change(path, value) {
    setDraft((current) => updateAt(current, path, value));
    setSaved(false);
  }

  async function onSubmit(event) {
    event.preventDefault();
    try {
      const next = await saveSetup(prepare(draft), token);
      setToken("");
      setSaved(true);
      setProblems([]);
      onSaved?.(next);
    } catch (exc) {
      setSaved(false);
      setProblems(exc.problems || [exc.message || "team.yaml не записан"]);
    }
  }

  return (
    <>
      <header className="top">
        <div>
          <h1>{team.name}</h1>
          <p className="sub">{stateNote(view)}</p>
          {saved ? <p className="sub">team.yaml записан. Слепок и manifest не менялись.</p> : null}
          {problems.length > 0 ? (
            <ul className="problems">
              {problems.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : null}
          <p className="sub">
            Идентификатор команды <code>{team.id}</code> этим экраном не меняется. Каталог формул остаётся версии {draft.catalogVersion}.
          </p>
          <p className="sub">Хеш правил складывается из календаря, статусов, эпиков, связей и состава задач. Его пишет build в manifest.</p>
        </div>
      </header>
      <form className="setup" onSubmit={onSubmit}>
        <Section title="Команда">
          <Field label="Название" name="team.name" value={team.name} onChange={(value) => change(["team", "name"], value)} />
          <Field label="PM" name="team.pm" value={team.pm} onChange={(value) => change(["team", "pm"], value)} />
          <Field label="Тимлид" name="team.teamLead" value={team.teamLead} onChange={(value) => change(["team", "teamLead"], value)} />
          <People draft={draft} onChange={setDraft} />
        </Section>
        <Section title="Календарь">
          <Field label="Часовой пояс" name="calendar.timezone" value={calendar.timezone} onChange={(value) => change(["calendar", "timezone"], value)} />
          <Field label="Рабочие дни" name="calendar.workdays" value={csv(calendar.workdays)} onChange={(value) => change(["calendar", "workdays"], splitNumbers(value))} />
          <Field label="Начало" name="calendar.workStart" value={calendar.workStart} onChange={(value) => change(["calendar", "workStart"], value)} />
          <Field label="Конец" name="calendar.workEnd" value={calendar.workEnd} onChange={(value) => change(["calendar", "workEnd"], value)} />
          <Field label="Перерыв, минут" name="calendar.breakMinutes" value={calendar.breakMinutes} onChange={(value) => change(["calendar", "breakMinutes"], asNumber(value, 0))} />
          <Field label="Начало перерыва" name="calendar.breakStart" value={calendar.breakStart} onChange={(value) => change(["calendar", "breakStart"], value)} />
          <Field label="Часов в дне" name="calendar.hoursPerDay" value={calendar.hoursPerDay} onChange={(value) => change(["calendar", "hoursPerDay"], asNumber(value, calendar.hoursPerDay))} />
          <Field label="Праздники" name="calendar.holidays" value={csv(calendar.holidays)} onChange={(value) => change(["calendar", "holidays"], splitText(value))} />
          <Field label="Дополнительные рабочие дни" name="calendar.extraWorkdays" value={csv(calendar.extraWorkdays)} onChange={(value) => change(["calendar", "extraWorkdays"], splitText(value))} />
        </Section>
        <Section title="Период">
          <Field label="Идентификатор" name="period.id" value={period.id} onChange={(value) => change(["period", "id"], value)} />
          <Field label="Начало" name="period.start" value={period.start} onChange={(value) => change(["period", "start"], value)} />
          <Field label="Конец" name="period.end" value={period.end} onChange={(value) => change(["period", "end"], value)} />
        </Section>
        <Section title="Jira">
          <Select label="Режим" name="sources.mode" value={sources.mode || "fixture"} options={MODES} onChange={(value) => change(["sources", "mode"], value)} />
          <Select label="Поставка" name="jira.deployment" value={jira.deployment || "server"} options={DEPLOYMENTS} onChange={(value) => change(["sources", "jira", "deployment"], value)} />
          <Field label="Адрес" name="jira.baseUrl" value={jira.baseUrl} onChange={(value) => change(["sources", "jira", "baseUrl"], value)} />
          <Field label="Доска" name="jira.boardId" value={jira.boardId} onChange={(value) => change(["sources", "jira", "boardId"], value)} />
          <Field label="Спринт" name="jira.sprintId" value={jira.sprintId} onChange={(value) => change(["sources", "jira", "sprintId"], value)} />
          <Field label="Имя переменной с токеном" name="jira.authEnv" value={jira.authEnv} onChange={(value) => change(["sources", "jira", "authEnv"], value)} />
          <Field label="Поле story points" name="jira.storyPoints" value={fields.storyPoints} onChange={(value) => change(["sources", "jira", "fields", "storyPoints"], value)} />
          <Field label="Поле эпика" name="jira.epicLink" value={fields.epicLink} onChange={(value) => change(["sources", "jira", "fields", "epicLink"], value)} />
        </Section>
        <Section title="Статусы">
          <Select label="Считать срок" name="workflow.usesDueDate" value={boolText(workflow.usesDueDate)} options={BOOLS} onChange={(value) => change(["workflow", "usesDueDate"], value === "true")} />
          <Statuses draft={draft} onChange={setDraft} />
        </Section>
        <Section title="Эпики и связи">
          <Field label="Приоритет" name="taxonomy.priority" value={csv(taxonomy.priority)} onChange={(value) => change(["taxonomy", "priority"], splitText(value))} />
          <Field label="Эпики проекта" name="epics.project" value={csv(taxonomy.epics?.project)} onChange={(value) => change(["taxonomy", "epics", "project"], splitText(value))} />
          <Field label="Эпики техники" name="epics.tech" value={csv(taxonomy.epics?.tech)} onChange={(value) => change(["taxonomy", "epics", "tech"], splitText(value))} />
          <Field label="Типы связей" name="linkTypes" value={csv(taxonomy.linkTypes)} onChange={(value) => change(["taxonomy", "linkTypes"], splitText(value))} />
          <Field label="Метка операционной работы" name="other.prodLabel" value={other.prodLabel} onChange={(value) => change(["taxonomy", "otherSubtype", "prodLabel"], value)} />
          <Field label="Метка прочей техники" name="other.techLabel" value={other.techLabel} onChange={(value) => change(["taxonomy", "otherSubtype", "techLabel"], value)} />
          <Rules draft={draft} onChange={setDraft} />
        </Section>
        <Section title="Состав задач">
          <Field label="Типы" name="scope.issueTypes" value={csv(scope.issueTypes)} onChange={(value) => change(["scope", "issueTypes"], splitText(value))} />
          <Field label="Проекты" name="scope.projectKeys" value={csv(scope.projectKeys)} onChange={(value) => change(["scope", "projectKeys"], splitText(value))} />
          <Select label="Считать сабтаски" name="scope.countSubtasks" value={boolText(scope.countSubtasks)} options={BOOLS} onChange={(value) => change(["scope", "countSubtasks"], value === "true")} />
        </Section>
        <Section title="Параметры формул">
          <p>Версия формулы остаётся 1. Здесь только параметры каталога.</p>
          <Field label="Минимальное пребывание, секунд" name="metrics.minStaySeconds" value={cycle.minStaySeconds ?? 900} onChange={(value) => change(["metrics", "cycleTime", "minStaySeconds"], asNumber(value, 900))} />
          <Field label="Высокие приоритеты" name="metrics.highPriorities" value={csv(hygiene.highPriorities)} onChange={(value) => change(["metrics", "hygiene", "highPriorities"], splitText(value))} />
          <Field label="Максимальный возраст, дней" name="metrics.maxAgeDays" value={hygiene.maxAgeDays ?? 90} onChange={(value) => change(["metrics", "hygiene", "maxAgeDays"], asNumber(value, 90))} />
          <Field label="Порог unknown, %" name="metrics.unknownWarnPct" value={classification.unknownWarnPct ?? 15} onChange={(value) => change(["metrics", "classification", "unknownWarnPct"], asNumber(value, 15))} />
        </Section>
        {view.writeTokenRequired ? (
          <label>
            Токен записи
            <input type="password" name="token" autoComplete="off" value={token} onChange={(event) => setToken(event.target.value)} />
          </label>
        ) : null}
        <button type="submit">Записать team.yaml</button>
      </form>
      <p className="sub">Секрет в файл не пишется: только имя переменной authEnv. Сборка с этого экрана не запускается.</p>
    </>
  );
}

function stateNote(view) {
  if (view.manifestState === "diff" || view.needsAcceptRecompute) {
    return "Хеш правил разошёлся с manifest. Следующий build остановится, пока не передан --accept-recompute.";
  }
  if (view.manifestState === "same") {
    return "Хеш правил совпадает с manifest.";
  }
  if (view.manifestState === "new") {
    return "Файл manifest ещё не создан. Его пишет build, не этот экран.";
  }
  return "Manifest не подключён. Запись меняет только team.yaml.";
}

function Section({ title, children }) {
  return (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, name, value, onChange }) {
  return (
    <label>
      {label}
      <input name={name} value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Select({ label, name, value, options, onChange }) {
  return (
    <label>
      {label}
      <select name={name} value={value ?? ""} onChange={(event) => onChange(event.target.value)}>
        {options.map(([item, caption]) => <option key={item || "empty"} value={item}>{caption}</option>)}
      </select>
    </label>
  );
}

function People({ draft, onChange }) {
  const members = draft.team?.members || [];
  const alumni = draft.team?.alumni || [];
  return (
    <>
      {members.map((person, index) => (
        <Person key={`member-${person.id || index}`} kind="member" index={index} person={person} draft={draft} onChange={onChange} />
      ))}
      {alumni.map((person, index) => (
        <Person key={`alumni-${person.id || index}`} kind="alumni" index={index} person={person} draft={draft} onChange={onChange} />
      ))}
      <button type="button" onClick={() => onChange(addPerson(draft))}>Добавить человека</button>
    </>
  );
}

function Person({ kind, index, person, draft, onChange }) {
  const prefix = `member.${kind}.${index}`;
  function edit(key, value) {
    onChange(updateAt(draft, ["team", kind === "alumni" ? "alumni" : "members", index, key], value));
  }
  return (
    <div className="setup-row">
      <Select label="Роль в файле" name={`${prefix}.kind`} value={kind} options={KINDS} onChange={(value) => onChange(movePerson(draft, kind, index, value))} />
      <Field label="id" name={`${prefix}.id`} value={person.id} onChange={(value) => edit("id", value)} />
      <Field label="Имя" name={`${prefix}.name`} value={person.name} onChange={(value) => edit("name", value)} />
      <Field label="Логин" name={`${prefix}.jiraUsername`} value={person.jiraUsername} onChange={(value) => edit("jiraUsername", value)} />
      <Field label="accountId" name={`${prefix}.jiraAccountId`} value={person.jiraAccountId} onChange={(value) => edit("jiraAccountId", value)} />
      <Field label="Роль" name={`${prefix}.role`} value={person.role} onChange={(value) => edit("role", value)} />
      <Field label="Ставка" name={`${prefix}.allocation`} value={person.allocation} onChange={(value) => edit("allocation", asNumber(value, person.allocation))} />
      <Field label="Ведёт эпики" name={`${prefix}.featureLeadOf`} value={csv(person.featureLeadOf)} onChange={(value) => edit("featureLeadOf", splitText(value))} />
      <Field label="Активен с" name={`${prefix}.activeFrom`} value={person.activeFrom} onChange={(value) => edit("activeFrom", value)} />
      <Field label="Активен по" name={`${prefix}.activeTo`} value={person.activeTo} onChange={(value) => edit("activeTo", value)} />
      <Absences person={person} prefix={prefix} onEdit={edit} />
      <button type="button" onClick={() => onChange(removePerson(draft, kind, index))}>Убрать из состава</button>
    </div>
  );
}

function Absences({ person, prefix, onEdit }) {
  const absences = person.absences || [];
  return (
    <>
      {absences.map((absence, index) => (
        <span key={`${absence.start}-${absence.end}-${index}`}>
          <Field label="Отсутствие с" name={`${prefix}.absence.${index}.start`} value={absence.start} onChange={(value) => onEdit("absences", replaceAt(absences, index, { ...absence, start: value }))} />
          <Field label="по" name={`${prefix}.absence.${index}.end`} value={absence.end} onChange={(value) => onEdit("absences", replaceAt(absences, index, { ...absence, end: value }))} />
        </span>
      ))}
      <button type="button" onClick={() => onEdit("absences", [...absences, { start: "", end: "" }])}>Добавить отсутствие</button>
    </>
  );
}

function Statuses({ draft, onChange }) {
  const rows = draft.workflow?.statusMap || [];
  return (
    <>
      {rows.map((row, index) => (
        <div className="setup-row" key={`${row.status}-${index}`}>
          <Field label="Статус" name={`status.${index}.status`} value={row.status} onChange={(value) => onChange(updateAt(draft, ["workflow", "statusMap", index, "status"], value))} />
          <Select label="Категория" name={`status.${index}.category`} value={row.category || "todo"} options={CATEGORIES} onChange={(value) => onChange(updateAt(draft, ["workflow", "statusMap", index, "category"], value))} />
          <Select label="Роль" name={`status.${index}.role`} value={row.role || "queue"} options={ROLES} onChange={(value) => onChange(updateAt(draft, ["workflow", "statusMap", index, "role"], value))} />
          <Select label="Исход" name={`status.${index}.outcome`} value={row.outcome || ""} options={OUTCOMES} onChange={(value) => onChange(updateAt(draft, ["workflow", "statusMap", index, "outcome"], value))} />
          <button type="button" onClick={() => onChange(removeAt(draft, ["workflow", "statusMap"], index))}>Убрать статус</button>
        </div>
      ))}
      <button type="button" onClick={() => onChange(updateAt(draft, ["workflow", "statusMap"], [...rows, { status: "", category: "todo", role: "queue" }]))}>Добавить статус</button>
    </>
  );
}

function Rules({ draft, onChange }) {
  const rows = draft.taxonomy?.rules || [];
  return (
    <>
      {rows.map((row, index) => {
        const when = row.when || {};
        return (
          <div className="setup-row" key={`rule-${index}`}>
            <Select label="Категория правила" name={`rule.${index}.category`} value={row.category || ""} options={RULE_CATEGORIES} onChange={(value) => onChange(updateAt(draft, ["taxonomy", "rules", index, "category"], value))} />
            <Field label="Метка" name={`rule.${index}.label`} value={when.label} onChange={(value) => onChange(updateAt(draft, ["taxonomy", "rules", index, "when", "label"], value))} />
            <Field label="Ключ проекта" name={`rule.${index}.projectKey`} value={when.projectKey} onChange={(value) => onChange(updateAt(draft, ["taxonomy", "rules", index, "when", "projectKey"], value))} />
          </div>
        );
      })}
      <button type="button" onClick={() => onChange(updateAt(draft, ["taxonomy", "rules"], [...rows, { category: "", when: {} }]))}>Добавить правило</button>
    </>
  );
}

function addPerson(draft) {
  const next = structuredClone(draft);
  next.team = next.team || {};
  next.team.members = [...(next.team.members || []), { id: "", name: "" }];
  return next;
}

function removePerson(draft, kind, index) {
  const key = kind === "alumni" ? "alumni" : "members";
  const next = structuredClone(draft);
  next.team[key] = (next.team[key] || []).filter((_, item) => item !== index);
  return next;
}

function movePerson(draft, fromKind, index, toKind) {
  if (fromKind === toKind) {
    return draft;
  }
  const fromKey = fromKind === "alumni" ? "alumni" : "members";
  const toKey = toKind === "alumni" ? "alumni" : "members";
  const next = structuredClone(draft);
  const from = next.team[fromKey] || [];
  const [person] = from.splice(index, 1);
  next.team[fromKey] = from;
  next.team[toKey] = [...(next.team[toKey] || []), person];
  return next;
}

function removeAt(source, path, index) {
  const next = structuredClone(source);
  const list = path.reduce((cursor, key) => cursor[key], next);
  list.splice(index, 1);
  return next;
}

function replaceAt(list, index, value) {
  return list.map((item, itemIndex) => (itemIndex === index ? value : item));
}

function updateAt(source, path, value) {
  const next = structuredClone(source);
  let cursor = next;
  for (let index = 0; index < path.length - 1; index += 1) {
    const key = path[index];
    if (cursor[key] == null || typeof cursor[key] !== "object") {
      cursor[key] = typeof path[index + 1] === "number" ? [] : {};
    }
    cursor = cursor[key];
  }
  cursor[path[path.length - 1]] = value;
  return next;
}

function prepare(draft) {
  const next = structuredClone(draft);
  const rows = next.workflow?.statusMap || [];
  for (const row of rows) {
    if (!row.outcome) {
      delete row.outcome;
    }
  }
  return next;
}

function csv(values) {
  if (!values || values.length === 0) {
    return "";
  }
  return values.join(", ");
}

function splitText(value) {
  return String(value).split(",").map((item) => item.trim()).filter(Boolean);
}

function splitNumbers(value) {
  const parts = splitText(value);
  if (parts.every((item) => item !== "" && Number.isFinite(Number(item)))) {
    return parts.map((item) => Number(item));
  }
  return parts;
}

function asNumber(value, fallback) {
  if (String(value).trim() === "") {
    return fallback;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : value;
}

function boolText(value) {
  return value ? "true" : "false";
}
