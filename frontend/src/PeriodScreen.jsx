import { coverageNotes } from "./api.js";
import { num } from "./format.js";
import { periodMetric } from "./links.js";
import { Epics } from "./period/Epics.jsx";
import { Hours } from "./period/Hours.jsx";
import { PeriodPeople } from "./period/People.jsx";
import { Hint } from "./widgets/Hint.jsx";

export function PeriodScreen({ team, error, onOpenSprint, onSaved }) {
  if (error) {
    return <p className="sub">{error}</p>;
  }
  if (!team) {
    return <p className="sub">Читаем слепок.</p>;
  }
  const period = team.period || {};
  const notes = coverageNotes(team.coverage);
  return (
    <>
      <div className="top">
        <div>
          <h1>{period.id}</h1>
          <p className="sub">{period.start} — {period.end}</p>
        </div>
        {notes.length > 0 ? <p className="note">{notes.join(" ")}</p> : null}
      </div>
      <Unknown view={team} />
      <Hours view={team} />
      <PeriodPeople view={team} />
      <Epics view={team} onSaved={onSaved} />
      <Completion view={team} onOpenSprint={onOpenSprint} />
    </>
  );
}

function Unknown({ view }) {
  const metric = periodMetric(view, "classification");
  if (!metric || !unknownRaised(metric)) {
    return null;
  }
  const threshold = metric.params?.unknownWarnPct;
  return (
    <div className="banner" data-widget="unknown" data-attention="true">
      <p>{`Не разобрано ${num(metric.value)}% при пороге ${num(threshold)}%.`}</p>
      <p>Плашка стоит над часами в статусе. Это покрытие классификации, не оценка команды. Путь каждой такой задачи — в списке людей, отметка «нет головы».</p>
    </div>
  );
}

function unknownRaised(metric) {
  if ((metric.warnings || []).includes("unknown-above-threshold")) {
    return true;
  }
  const value = metric.value;
  const threshold = metric.params?.unknownWarnPct;
  if (typeof value !== "number" || typeof threshold !== "number") {
    return false;
  }
  return value > threshold;
}

function Completion({ view, onOpenSprint }) {
  const metric = view.completion || {};
  const detail = metric.detail || {};
  const incomplete = view.coverage?.membership === "incomplete";
  const ready = metric.value != null && !incomplete && Object.keys(detail).length > 0;
  return (
    <section data-widget="completion">
      <h2>Завершение к старту спринта</h2>
      <Hint>Это число уже лежит на экране спринта. Здесь оно не пересчитывается. Ссылка открывает тот экран.</Hint>
      {ready ? (
        <p>
          <a href="#sprint" onClick={(event) => { event.preventDefault(); onOpenSprint?.(); }}>
            {`${num(detail.done)} из ${num(detail.committed)}`}
          </a>
        </p>
      ) : <p>—</p>}
    </section>
  );
}
