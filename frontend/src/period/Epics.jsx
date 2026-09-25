import { useState } from "react";
import { saveEdit } from "../api.js";
import { num } from "../format.js";
import { periodMetric } from "../links.js";
import { Hint } from "../widgets/Hint.jsx";
import { IssueLink } from "../widgets/IssueLink.jsx";

export function Epics({ view, onSaved }) {
  const metric = periodMetric(view, "projectList") || {};
  const warnings = metric.warnings || [];
  const rows = metric.detail?.rows || [];
  const notices = warnings.map(noticeText).filter(Boolean);
  const names = Object.fromEntries(
    (view.people?.detail?.rows || []).filter((item) => item.name).map((item) => [item.personId, item.name]),
  );
  const showTable = rows.length > 0 && !warnings.includes("no-epics");
  return (
    <section data-widget="epics">
      <h2>Эпики</h2>
      <Hint>
        Релиз и заметка приходят из файла правок, не из Jira. Чужой ключ эпика остаётся предупреждением. Число метрики форма не меняет.
      </Hint>
      {notices.length > 0 ? (
        <div className="banner" data-widget="epic-warnings">
          {notices.map((item) => <p key={item}>{item}</p>)}
        </div>
      ) : null}
      {showTable ? (
        <table>
          <thead>
            <tr>
              <th>Ключ</th>
              <th>Название</th>
              <th>Статус</th>
              <th>Feature lead</th>
              <th>Релиз</th>
              <th>Заметка</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td><IssueLink view={view} issueKey={row.key} /></td>
                <td>{row.name ?? ""}</td>
                <td>{num(row.status)}</td>
                <td>{num(names[row.featureLead] || row.featureLead)}</td>
                <td>{num(row.release)}</td>
                <td {...(row.note ? { "data-attention": "true" } : {})}>{num(row.note)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {view.editsEnabled ? <EditForm view={view} onSaved={onSaved} /> : null}
    </section>
  );
}

function noticeText(warning) {
  const text = String(warning);
  if (text === "no-epics") {
    return "Список эпиков пуст. Пустая таблица не рисуется.";
  }
  if (text === "edits-team-mismatch") {
    return "Файл правок другой команды. Пометки не подставлены.";
  }
  if (text.startsWith("unknown-epic:")) {
    return `Чужой эпик ${text.slice("unknown-epic:".length)} в правках. Запись не скрыта.`;
  }
  return "";
}

function EditForm({ view, onSaved }) {
  const [problem, setProblem] = useState("");
  async function onSubmit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields = {
      epicId: data.get("epicId"),
      release: data.get("release"),
      text: data.get("text"),
      author: data.get("author"),
    };
    if (view.writeTokenRequired) {
      fields.token = data.get("token");
    }
    try {
      await saveEdit(fields);
      setProblem("");
      onSaved?.();
    } catch (exc) {
      setProblem(exc.message || "пометка не записалась");
    }
  }
  return (
    <form className="edits" onSubmit={onSubmit}>
      <label>Эпик <input name="epicId" required /></label>
      <label>Релиз <input name="release" /></label>
      <label>Заметка <textarea name="text" rows="3" /></label>
      <label>Автор <input name="author" required /></label>
      {view.writeTokenRequired ? (
        <label>Токен записи <input type="password" name="token" autoComplete="off" /></label>
      ) : null}
      <button type="submit">Сохранить пометку</button>
      {problem ? <p className="problems">{problem}</p> : null}
    </form>
  );
}
