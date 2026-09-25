import { duration, num, ratio } from "../format.js";
import { periodMetric } from "../links.js";
import { Hint } from "../widgets/Hint.jsx";

export function Hours({ view }) {
  const metric = periodMetric(view, "statusHours") || {};
  const detail = metric.detail || {};
  const timing = view?.coverage?.timing;
  const days = detail.days || [];
  const hidden = timing === "none" || (metric.value == null && days.length === 0);
  const inherited = seconds(detail.inheritedSeconds);
  const own = seconds(detail.ownSeconds);
  return (
    <section data-widget="hours">
      <h2>Часы в статусе</h2>
      <p>Часы в статусе, не списание.</p>
      <Hint>
        Кольцо делит уже посчитанные секунды на две части: начатые в этом периоде и пришедшие из прошлого. Доля к ёмкости и параллельность — диагностика, на экране два знака. Цвета нормы нет, целью эти числа не являются. Строка дня показывает секунды одного человека до масштаба и после.
      </Hint>
      {hidden ? (
        <p>{`Ряд скрыт: coverage.timing = ${timing ?? ""}. Нулевая шкала не рисуется.`}</p>
      ) : (
        <div className="hours">
          <Ring inherited={inherited} own={own} />
          <div>
            <p>Пришли из прошлого {inherited > 0 ? <span data-attention="true">{duration(inherited)}</span> : duration(inherited)}</p>
            <p>{`Начаты в этом периоде ${duration(own)}`}</p>
            <p data-diagnostic="parallelism">{`Параллельность ${ratio(detail.parallelism)}`}</p>
            <p data-diagnostic="ratio">{`Доля к ёмкости ${ratio(metric.value)}`}</p>
            <p className="legend">
              <span><i className="swatch swatch-own" />свои</span>
              <span><i className="swatch swatch-inherited" />из прошлого</span>
            </p>
          </div>
        </div>
      )}
      {hidden ? null : (
        <details>
          <summary>Секунды по людям и дням</summary>
          <ul>
            {days.map((row) => (
              <li key={`${row.personId}-${row.date}`} {...(row.outside ? { "data-attention": "true" } : {})}>
                {`${row.personId ?? ""} ${row.date ?? ""}${row.outside ? " вне состава" : ""}: до масштаба ${num(row.rawSeconds)} с, после ${num(row.scaledSeconds)} с`}
              </li>
            ))}
          </ul>
        </details>
      )}
      {metric.explain ? <p className="explain">{metric.explain}</p> : null}
    </section>
  );
}

function Ring({ inherited, own }) {
  const total = inherited + own;
  if (total <= 0) {
    return null;
  }
  const radius = 42;
  const circle = 2 * Math.PI * radius;
  const ownLen = circle * own / total;
  const inheritedLen = circle * inherited / total;
  const turn = "rotate(-90 60 60)";
  return (
    <svg className="ring" viewBox="0 0 120 120" role="img" aria-label="Кольцо часов: свои и пришедшие из прошлого">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--line)" strokeWidth="14" />
      <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--ink)" strokeWidth="14" strokeDasharray={`${ownLen.toFixed(2)} ${circle.toFixed(2)}`} strokeDashoffset="0" transform={turn} />
      <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--brass)" strokeWidth="14" strokeDasharray={`${inheritedLen.toFixed(2)} ${circle.toFixed(2)}`} strokeDashoffset={(-ownLen).toFixed(2)} transform={turn} />
    </svg>
  );
}

function seconds(value) {
  if (typeof value !== "number") {
    return 0;
  }
  return Math.trunc(value);
}
