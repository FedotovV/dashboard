import { positive } from "../format.js";
import { reasonLabel } from "../labels.js";
import { metricOf } from "../links.js";
import { Figure } from "./Figure.jsx";
import { Hint } from "./Hint.jsx";
import { IssueLink } from "./IssueLink.jsx";

export function Blockers({ view }) {
  const metric = metricOf(view, "blockers");
  if (!metric) {
    return null;
  }
  const items = metric.detail?.items || [];
  return (
    <section data-widget="blockers">
      <h2>Блокеры</h2>
      <Hint>
        Список причин, не балл. Сверху просроченный срок, затем пауза, затем работа без исполнителя. Ключ открывает задачу в Jira.
      </Hint>
      <Figure value={metric.value} attention={positive(metric.value)} />
      <ol>
        {items.length > 0 ? items.map((item) => {
          const reasons = item.reasons || [];
          const token = reasons[0] || "";
          const labels = reasons.map((reason) => reasonLabel(reason)).join(", ");
          return (
            <li data-reason={token} data-attention="true" key={`${item.issueKey}-${token}`}>
              <IssueLink view={view} issueKey={item.issueKey} />
              {`: ${labels}`}
            </li>
          );
        }) : <li>Список пуст</li>}
      </ol>
    </section>
  );
}
