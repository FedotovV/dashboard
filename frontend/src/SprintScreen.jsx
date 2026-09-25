import { coverageNotes } from "./api.js";
import { Flow } from "./widgets/Flow.jsx";
import { Scope } from "./widgets/Scope.jsx";
import { Timing } from "./widgets/Timing.jsx";

export function SprintScreen({ sprint, error }) {
  if (error) {
    return <p className="sub">{error}</p>;
  }
  if (!sprint) {
    return <p className="sub">Читаем слепок.</p>;
  }
  const body = sprint.sprint || {};
  const notes = coverageNotes(sprint.coverage);
  return (
    <>
      <div className="top">
        <div>
          <h1>{body.id}</h1>
          <p className="sub">{body.start} — {body.end}</p>
        </div>
        {notes.length > 0 ? <p className="note">{notes.join(" ")}</p> : null}
      </div>
      <Scope view={sprint} />
      <Flow view={sprint} />
      <Timing view={sprint} />
    </>
  );
}
