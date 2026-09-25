import { duration } from "../format.js";
import { reasonLabel } from "../labels.js";
import { metricOf } from "../links.js";
import { Figure } from "./Figure.jsx";
import { Hint } from "./Hint.jsx";
import { IssueLink } from "./IssueLink.jsx";

export function Timing({ view }) {
  return (
    <section data-widget="timing">
      <h2>Цикл и ожидание</h2>
      <Hint>
        Число — медиана рабочих дней среди закрытых задач. Цикл считает время в работе, ожидание — время в ревью или тесте. Раскройте список: у каждой задачи секунды из слепка и понятная причина, если она в медиану не вошла. Заход короче минимального пребывания отбрасывается. Если задачу закрыли и открыли снова, считаются оба захода до текущего закрытия.
      </Hint>
      <div className="grid">
        <TimingCard view={view} metricId="cycleTime" title="Цикл" roleWords="в работе" />
        <TimingCard view={view} metricId="waitTime" title="Ожидание" roleWords="в ожидании" />
      </div>
    </section>
  );
}

function TimingCard({ view, metricId, title, roleWords }) {
  const metric = metricOf(view, metricId) || {};
  const perIssue = metric.detail?.perIssue || [];
  const seen = new Set(perIssue.map((item) => item.issueKey));
  const rows = perIssue.map((item) => {
    const seconds = item.seconds;
    return (
      <li key={`in-${item.issueKey}`} {...(Number.isInteger(seconds) ? { "data-seconds": String(seconds) } : {})}>
        <IssueLink view={view} issueKey={item.issueKey} />
        {` вошла в медиану: ${duration(seconds)} ${roleWords}. Очередь и короткие заходы в это число не входят.`}
      </li>
    );
  });
  for (const key of metric.population || []) {
    if (!seen.has(key)) {
      rows.push(
        <li key={`pop-${key}`}>
          <IssueLink view={view} issueKey={key} /> есть в составе медианы.
        </li>,
      );
    }
  }
  const excluded = (metric.excluded || []).map((item) => (
    <li key={`out-${item.issueKey}-${item.reason}`} data-attention="true">
      <IssueLink view={view} issueKey={item.issueKey} />
      {` не вошла в медиану: ${reasonLabel(item.reason)}. Такой заход не двигает число, чтобы случайный переход статуса не выглядел как работа.`}
    </li>
  ));
  return (
    <article className="card" data-metric={metricId}>
      <h2>{title}</h2>
      <Figure value={metric.value} />
      <p className="explain">{metric.explain || ""}</p>
      <p className="key">Что вошло в число</p>
      <ul>{rows.length > 0 ? rows : <li>в сумму никто не вошёл</li>}</ul>
      <ul data-excluded="true">{excluded}</ul>
    </article>
  );
}
