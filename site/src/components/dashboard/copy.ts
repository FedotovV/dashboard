export type Coverage = {
  timing?: string;
  membership?: string;
};

export function coverageNotes(coverage: Coverage | undefined): string[] {
  const notes: string[] = [];
  const timing = coverage?.timing;
  if (timing === 'none' || timing === 'partial') {
    notes.push(`Тайминги: coverage.timing = ${timing}`);
  }
  if (coverage?.membership === 'incomplete') {
    notes.push('Состав: coverage.membership = incomplete');
  }
  return notes;
}

export function manifestNote(view: { manifestState?: string; needsAcceptRecompute?: boolean }): string {
  const state = view.manifestState;
  if (state === 'diff' || view.needsAcceptRecompute) {
    return 'Хеш правил разошёлся с manifest. Следующий build остановится, пока не передан --accept-recompute.';
  }
  if (state === 'same') {
    return 'Хеш правил совпадает с manifest.';
  }
  if (state === 'new') {
    return 'Файл manifest ещё не создан. Его пишет build, не этот экран.';
  }
  return 'Manifest не подключён. Запись меняет только team.yaml.';
}

export async function loadJson(path: string): Promise<unknown> {
  const response = await fetch(path);
  const text = await response.text();
  if (!response.ok) {
    let message = text.trim() || 'слепок не открылся';
    try {
      const parsed = JSON.parse(text) as { error?: unknown };
      if (typeof parsed.error === 'string' && parsed.error.trim()) {
        message = parsed.error.trim();
      }
    } catch {
      /* тело уже текст сервера */
    }
    throw new Error(message);
  }
  return JSON.parse(text) as unknown;
}
