import { num } from "../format.js";
import { metricOf } from "../links.js";
import { Hint } from "./Hint.jsx";

export function Burndown({ view }) {
  const metric = metricOf(view, "burndown");
  if (view?.coverage?.storyPoints !== "full" || !metric || metric.value == null) {
    return null;
  }
  const points = metric.detail?.points || [];
  return (
    <section data-widget="burndown">
      <h2>Burndown</h2>
      <Hint>
        Ось Y — story points на момент входа в спринт. Ось X — рабочие дни спринта: суббота, воскресенье и официальные праздники в расчёт и на график не попадают. Пунктир — ровное сгорание по этим дням. Сплошная линия — факт. Если факт выше пунктира, остаток выделен: работа сгорает медленнее плана.
      </Hint>
      <p className="axes">Y — количество SP. X — рабочие дни спринта.</p>
      <p className="remainder">Остаток <span {...(behind(points) ? { "data-attention": "true" } : {})}>{num(metric.value)}</span></p>
      <Spark points={points} />
      <table>
        <thead>
          <tr>
            <th>Рабочий день</th>
            <th>Идеал, SP</th>
            <th>Факт, SP</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.date}>
              <td>{point.date ?? ""}</td>
              <td>{num(point.ideal)}</td>
              <td>{num(point.actual)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function behind(points) {
  if (!points.length) {
    return false;
  }
  const last = points[points.length - 1];
  const actual = last.actual;
  const ideal = last.ideal;
  if (typeof actual !== "number" || typeof ideal !== "number") {
    return false;
  }
  return actual > ideal;
}

function Spark({ points }) {
  if (points.length < 2) {
    return null;
  }
  const width = 440;
  const height = 180;
  const left = 44;
  const right = 16;
  const topPad = 18;
  const bottom = 32;
  const plotW = width - left - right;
  const plotH = height - topPad - bottom;
  const top = Math.max(1, ...numbers(points, "actual"), ...numbers(points, "ideal"));
  const yZero = topPad + plotH;
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Burndown: ось Y story points, ось X рабочие дни спринта">
      <text x="8" y="14" className="axis">SP</text>
      <text x={left} y={height - 8} className="axis">дни спринта</text>
      <line x1={left} y1={topPad} x2={left} y2={yZero} className="frame" />
      <line x1={left} y1={yZero} x2={width - right} y2={yZero} className="frame" />
      <polyline className="ideal" points={line(points, "ideal", left, plotW, topPad, plotH, top)} />
      <polyline className="actual" points={line(points, "actual", left, plotW, topPad, plotH, top)} />
    </svg>
  );
}

function numbers(points, key) {
  return points.map((point) => point[key]).filter((value) => typeof value === "number");
}

function line(points, key, left, plotW, topPad, plotH, top) {
  const coords = [];
  points.forEach((point, index) => {
    const value = point[key];
    if (typeof value !== "number") {
      return;
    }
    const x = points.length === 1 ? left : left + (index * plotW) / (points.length - 1);
    const y = topPad + plotH - (value / top) * plotH;
    coords.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  });
  return coords.join(" ");
}
