import { num, positive } from "../format.js";
import { metricOf } from "../links.js";
import { Hint } from "./Hint.jsx";
import { IssueLink } from "./IssueLink.jsx";

const PERSON_STATS = [
  ["total", "Всего задач"],
  ["backlog", "Бэклог"],
  ["inProgress", "В работе"],
  ["paused", "Пауза"],
  ["testing", "Тестируются"],
  ["done", "Завершены"],
  ["canceled", "Отменены"],
];

const MIX = [
  ["backlog", "mix-backlog"],
  ["inProgress", "mix-progress"],
  ["testing", "mix-testing"],
  ["paused", "mix-paused"],
  ["done", "mix-done"],
  ["canceled", "mix-canceled"],
  ["unknown", "mix-unknown"],
];

const ATTENTION_STATS = new Set(["paused", "canceled"]);

export function People({ view }) {
  const metric = metricOf(view, "personLoad");
  if (!metric) {
    return null;
  }
  const rows = metric.detail?.rows || [];
  return (
    <section data-widget="people">
      <h2>Команда</h2>
      <Hint>
        Под фамилией — задачи этого человека в текущем спринте. Бэклог — очередь, в работе — уже взято, пауза — блок или ожидание решения, тестируются — ревью, завершены — закрыто как сделанное. SP — сумма текущих story points, пустая оценка в сумму не входит. Полоска повторяет эти же счётчики. Человек без открытых задач остаётся в составе.
      </Hint>
      <div className="people">
        {rows.map((row) => <Person key={row.personId} view={view} row={row} />)}
      </div>
    </section>
  );
}

function Person({ view, row }) {
  const [surname, rest] = nameParts(row);
  if (!Object.hasOwn(row, "total")) {
    const keys = row.openKeys || [];
    return (
      <article className="person" data-person={row.personId}>
        <h3>{surname}</h3>
        {keys.length > 0 ? <KeyColumn view={view} keys={keys} /> : <p>нет открытых</p>}
      </article>
    );
  }
  const subtitle = [rest, row.personId].filter(Boolean).join(" · ");
  return (
    <article className="person" data-person={row.personId}>
      <h3>{surname}</h3>
      <p className="who">{subtitle}</p>
      <dl className="stats">
        {PERSON_STATS.map(([key, label]) => (
          <div data-stat={key} key={key}>
            <dt>{label}</dt>
            <dd {...(ATTENTION_STATS.has(key) && positive(row[key]) ? { "data-attention": "true" } : {})}>{num(row[key])}</dd>
          </div>
        ))}
        <div data-stat="storyPoints">
          <dt>Story points</dt>
          <dd>{num(row.storyPoints)}</dd>
        </div>
        <div data-stat="openStoryPoints">
          <dt>Открытые SP</dt>
          <dd>{num(row.openStoryPoints)}</dd>
        </div>
        {positive(row.pointsMissing) ? (
          <div data-stat="pointsMissing">
            <dt>Без оценки</dt>
            <dd data-attention="true">{num(row.pointsMissing)}</dd>
          </div>
        ) : null}
      </dl>
      <Mix row={row} />
      <PersonTasks view={view} row={row} />
      {(row.openKeys || []).length === 0 ? <p>нет открытых</p> : null}
    </article>
  );
}

function PersonTasks({ view, row }) {
  const issues = row.issues || [];
  if (issues.length === 0) {
    return <KeyColumn view={view} keys={row.openKeys || []} />;
  }
  return (
    <ol className="tasks">
      {issues.map((issue) => {
        const points = issue.storyPoints;
        const pointLabel = points == null ? "" : ` · ${num(points)} SP`;
        return (
          <li data-attention={issue.role === "hold" ? "true" : undefined} key={issue.key}>
            <IssueLink view={view} issueKey={issue.key} />
            <span className="task-name">{issue.summary ?? ""}</span>
            <span className="task-meta">{`${issue.status ?? ""}${pointLabel}`}</span>
          </li>
        );
      })}
    </ol>
  );
}

function KeyColumn({ view, keys }) {
  if (!keys.length) {
    return null;
  }
  return (
    <ol className="tasks">
      {keys.map((key) => (
        <li key={key}><IssueLink view={view} issueKey={key} /></li>
      ))}
    </ol>
  );
}

function Mix({ row }) {
  const total = row.total;
  if (typeof total !== "number" || total <= 0) {
    return null;
  }
  const parts = [];
  for (const [key, css] of MIX) {
    const count = row[key] || 0;
    if (typeof count !== "number" || count <= 0) {
      continue;
    }
    parts.push(<span className={css} key={key} style={{ width: `${(count / total * 100).toFixed(4)}%` }} />);
  }
  if (parts.length === 0) {
    return null;
  }
  return <div className="mix" aria-hidden="true">{parts}</div>;
}

function nameParts(row) {
  const name = row.name || row.personId || "";
  const text = String(name).trim();
  if (row.name && text.includes(" ")) {
    const space = text.indexOf(" ");
    return [text.slice(0, space), text.slice(space + 1)];
  }
  return [text, ""];
}
