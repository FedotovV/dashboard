import { num } from "../format.js";
import { ROLES } from "../labels.js";
import { Hint } from "./Hint.jsx";

export function Trend({ view }) {
  const trend = view?.sprint?.trend || {};
  const previous = trend.previous;
  const sparkline = trend.sparkline || [];
  return (
    <section data-widget="trend">
      <h2>Тренд</h2>
      <Hint>
        Точка появляется только в день, когда слепок уже записан, и добавляется сегодня. Пустые дни между слепками не дорисовываются. Бейдж — последний слепок прошлого спринта, если он есть.
      </Hint>
      {previous ? <Previous previous={previous} /> : null}
      <TrendLine points={sparkline} />
      <ul>
        {sparkline.map((point) => (
          <li data-date={point.date} key={point.date}>
            {`${point.date ?? ""}: ${num(point.done)}`}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Previous({ previous }) {
  const byRole = previous.byRole || {};
  const bits = ROLES.map((role) => `${role} ${num(byRole[role])}`).join(" ");
  return (
    <p data-widget="previous">
      {`Прошлый спринт ${previous.sprintId ?? ""} (${previous.snapshotId ?? ""}): ${bits}`}
    </p>
  );
}

function TrendLine({ points }) {
  if (points.length < 2) {
    return null;
  }
  const width = 440;
  const height = 72;
  const left = 8;
  const right = 8;
  const topPad = 8;
  const bottom = 8;
  const plotW = width - left - right;
  const plotH = height - topPad - bottom;
  const values = points.map((point) => point.done).filter((value) => typeof value === "number");
  const top = Math.max(1, ...values);
  const coords = [];
  points.forEach((point, index) => {
    if (typeof point.done !== "number") {
      return;
    }
    const x = left + (index * plotW) / (points.length - 1);
    const y = topPad + plotH - (point.done / top) * plotH;
    coords.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  });
  return (
    <svg className="chart spark" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Спарклайн закрытых задач по дням слепка">
      <polyline className="actual" points={coords.join(" ")} />
    </svg>
  );
}
