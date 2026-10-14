import { useEffect, useState } from 'react';
import { coverageNotes, loadJson, manifestNote, type Coverage } from './copy';

type Kind = 'sprint' | 'period' | 'setup';

type SprintBody = {
  teamId?: string;
  coverage?: Coverage;
  sprint?: { id?: string; start?: string; end?: string };
};

type PeriodBody = {
  teamId?: string;
  coverage?: Coverage;
  period?: { id?: string; start?: string; end?: string };
};

type SetupBody = {
  document?: { team?: { id?: string; name?: string } };
  manifestState?: string;
  needsAcceptRecompute?: boolean;
};

const LABELS: Record<Kind, string> = {
  sprint: 'Спринт',
  period: 'Период',
  setup: 'Настройка',
};

const PATHS: Record<Kind, string> = {
  sprint: '/api/sprint',
  period: '/api/team',
  setup: '/api/setup',
};

export default function DashboardScreen({ kind }: { kind: Kind }) {
  const [title, setTitle] = useState(LABELS[kind]);
  const [subtitle, setSubtitle] = useState('Читаем слепок.');
  const [teamLine, setTeamLine] = useState('');
  const [notes, setNotes] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    loadJson(PATHS[kind])
      .then((payload) => {
        if (!active) {
          return;
        }
        const next = readPayload(kind, payload);
        setTitle(next.title);
        setSubtitle(next.subtitle);
        setTeamLine(next.teamLine);
        setNotes(next.notes);
      })
      .catch((exc: unknown) => {
        if (!active) {
          return;
        }
        setTitle(LABELS[kind]);
        setSubtitle(exc instanceof Error ? exc.message : 'слепок не открылся');
        setTeamLine('');
        setNotes([]);
      });
    return () => {
      active = false;
    };
  }, [kind]);

  return (
    <>
      <section className="relative not-prose">
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
          <div className="pt-8 md:pt-12 pb-4 text-center max-w-5xl mx-auto">
            <p className="text-base text-secondary dark:text-blue-200 font-bold tracking-wide uppercase">
              {LABELS[kind]}
            </p>
            <h1 className="text-5xl md:text-6xl font-bold leading-tighter tracking-tighter mb-4 font-heading text-heading">
              {title}
            </h1>
            <p className="text-xl text-muted mb-2 dark:text-slate-300">{subtitle}</p>
            {teamLine ? <p className="text-muted">{teamLine}</p> : null}
          </div>
        </div>
      </section>
      {notes.length > 0 ? (
        <section className="not-prose bg-blue-50 dark:bg-slate-800" data-widget="coverage">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 text-md text-center font-medium">
            <p>{notes.join(' ')}</p>
          </div>
        </section>
      ) : null}
    </>
  );
}

function readPayload(
  kind: Kind,
  payload: unknown
): { title: string; subtitle: string; teamLine: string; notes: string[] } {
  if (kind === 'setup') {
    const body = payload as SetupBody;
    const team = body.document?.team;
    return {
      title: team?.name || LABELS.setup,
      subtitle: manifestNote(body),
      teamLine: team?.id ? `Команда ${team.id}` : '',
      notes: [],
    };
  }
  const body = payload as SprintBody & PeriodBody;
  const range = kind === 'sprint' ? body.sprint : body.period;
  return {
    title: range?.id || LABELS[kind],
    subtitle: rangeLine(range?.start, range?.end),
    teamLine: body.teamId ? `Команда ${body.teamId}` : '',
    notes: coverageNotes(body.coverage),
  };
}

function rangeLine(start: string | undefined, end: string | undefined): string {
  if (!start && !end) {
    return '—';
  }
  return `${start || '—'} — ${end || '—'}`;
}
