import { periodMetric } from "../links.js";
import { Hint } from "../widgets/Hint.jsx";
import { IssueLink } from "../widgets/IssueLink.jsx";

const CATEGORIES = {
  project: "проект",
  tech: "техника",
  other: "другое",
  unknown: "не разобрано",
};

export function PeriodPeople({ view }) {
  const metric = periodMetric(view, "classification") || {};
  const paths = metric.detail?.paths || [];
  const issues = Object.fromEntries((view.issues || []).map((item) => [item.key, item]));
  const roster = new Map();
  const order = [];
  for (const row of view.people?.detail?.rows || []) {
    roster.set(row.personId, row);
    order.push(row.personId);
  }
  const groups = new Map();
  for (const path of paths) {
    const issue = issues[path.issueKey] || {};
    const personId = issue.assigneeId ?? null;
    const list = groups.get(personId) || [];
    list.push(path);
    groups.set(personId, list);
  }
  const personIds = order.filter((personId) => groups.has(personId));
  for (const personId of groups.keys()) {
    if (!personIds.includes(personId)) {
      personIds.push(personId);
    }
  }
  return (
    <section data-widget="people">
      <h2>Люди</h2>
      <Hint>
        Под именем — ключи периода и путь классификации из слепка: голова эпика, правило, явная метка или «нет головы». Дерево на экране заново не обходится. Выделено то, что осталось без головы.
      </Hint>
      <div className="people">
        {personIds.map((personId) => {
          const row = roster.get(personId) || {};
          const title = personId ? (row.name || personId) : "Без исполнителя";
          return (
            <article className="person" key={personId ?? "none"}>
              <h3>{title}</h3>
              <ul className="tasks">
                {groups.get(personId).map((path) => {
                  const unknown = path.reason === "unknown" || path.category === "unknown";
                  return (
                    <li key={path.issueKey} {...(unknown ? { "data-attention": "true" } : {})}>
                      <IssueLink view={view} issueKey={path.issueKey} />
                      <span className="path">{` ${pathText(path)}`}</span>
                    </li>
                  );
                })}
              </ul>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function pathText(path) {
  const category = CATEGORIES[path.category] || path.category || "";
  if (path.reason === "head" && path.headId) {
    return `голова ${path.headId}, ${category}`;
  }
  if (path.reason === "rule") {
    return `правило, ${category}`;
  }
  if (path.reason === "label") {
    return `метка ${path.subtype || ""}, ${category}`.trim();
  }
  return "нет головы";
}
