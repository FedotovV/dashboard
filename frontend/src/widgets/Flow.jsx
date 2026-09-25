import { positive } from "../format.js";
import { ATTENTION_ROLES, ROLE_LABELS, ROLES } from "../labels.js";
import { metricOf } from "../links.js";
import { Figure } from "./Figure.jsx";
import { Hint } from "./Hint.jsx";

export function Flow({ view }) {
  const metric = metricOf(view, "sprintFlow");
  const byRole = metric?.detail?.byRole || {};
  return (
    <section data-widget="flow">
      <h2>Поток</h2>
      <Hint>
        Каждая задача текущего состава сидит в одной роли. Пауза и отмена выделены: с них начинается разбор. Очередь — ещё не взяли, ожидание — ревью или тест, сделано — закрыто как выполненное.
      </Hint>
      <div className="roles">
        {ROLES.map((role) => {
          const number = byRole[role];
          return (
            <article className="card" data-role={role} key={role}>
              <span className="key">{role}</span>
              <h2>{ROLE_LABELS[role]}</h2>
              <Figure value={number} attention={ATTENTION_ROLES.has(role) && positive(number)} />
            </article>
          );
        })}
      </div>
    </section>
  );
}
