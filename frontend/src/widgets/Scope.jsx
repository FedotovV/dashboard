import { positive } from "../format.js";
import { ATTENTION_SCOPE, SCOPE_KEYS, SCOPE_LABELS } from "../labels.js";
import { metricOf } from "../links.js";
import { Figure } from "./Figure.jsx";
import { Hint } from "./Hint.jsx";

export function Scope({ view }) {
  const scope = metricOf(view, "scopeChange");
  const completion = metricOf(view, "completionVsCommitted");
  const detail = scope?.detail || {};
  const incomplete = view?.coverage?.membership === "incomplete";
  return (
    <section data-widget="scope">
      <h2>Состав</h2>
      <Hint>
        «На старте» — задачи, которые уже были в спринте в день старта. «Добавлены» и «Сняты» — движение после старта, они выделены. Завершение считает сделанное среди стартового состава. Отменённые остаются в знаменателе и долю не увеличивают.
      </Hint>
      <div className="grid">
        {SCOPE_KEYS.map((key) => {
          const number = incomplete ? null : detail[key];
          return (
            <article className="card" data-scope={key} key={key}>
              <span className="key">{key}</span>
              <h2>{SCOPE_LABELS[key]}</h2>
              <Figure value={number} attention={positive(number) && ATTENTION_SCOPE.has(key)} />
            </article>
          );
        })}
      </div>
      <p className="completion" data-completion="true">{completionLine(completion, incomplete)}</p>
    </section>
  );
}

function completionLine(metric, incomplete) {
  if (!metric || incomplete || metric.value == null) {
    return "Завершение к старту: состав на старте не собран";
  }
  const detail = metric.detail || {};
  if (detail.done == null || detail.committed == null) {
    return "Завершение к старту: состав на старте не собран";
  }
  return `Завершение к старту: ${Math.trunc(detail.done)} из ${Math.trunc(detail.committed)}`;
}
