import { positive } from "../format.js";
import { reasonLabel } from "../labels.js";
import { metricOf } from "../links.js";
import { Figure } from "./Figure.jsx";
import { Hint } from "./Hint.jsx";
import { IssueLink } from "./IssueLink.jsx";

export function Hygiene({ view }) {
  const metric = metricOf(view, "hygiene");
  if (!metric) {
    return null;
  }
  const items = metric.detail?.items || [];
  return (
    <section data-widget="hygiene">
      <h2>Качество данных</h2>
      <p className="footnote">
        Это не оценка команды. Плашка значит, что у задачи не хватает поля, без которого соседние числа врут: нет story points, нет исполнителя у работы в процессе, нет срока, высокий приоритет всё ещё в очереди или задача старше порога. Откройте ключ, заполните поле в задаче и дождитесь следующего слепка: плашка уйдёт. Просроченный срок сюда не входит, он в блокерах.
      </p>
      <Hint>Смотрите на выделенные ключи. Ноль плашек — поля, которые просит каталог, на месте.</Hint>
      <Figure value={metric.value} attention={positive(metric.value)} />
      <ul>
        {items.length > 0 ? items.map((item) => (
          <li data-attention="true" key={`${item.issueKey}-${item.reason}`}>
            <IssueLink view={view} issueKey={item.issueKey} />
            {`: ${reasonLabel(item.reason)}`}
          </li>
        )) : <li>Плашек нет</li>}
      </ul>
    </section>
  );
}
