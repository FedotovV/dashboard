export const ROLES = ["active", "wait", "hold", "queue", "done", "canceled", "total"];

export const ROLE_LABELS = {
  active: "В работе",
  wait: "Ожидание",
  hold: "Пауза",
  queue: "Очередь",
  done: "Сделано",
  canceled: "Отменено",
  total: "Всего",
};

export const SCOPE_KEYS = ["committed", "added", "removed"];

export const SCOPE_LABELS = {
  committed: "На старте",
  added: "Добавлены",
  removed: "Сняты",
};

export const REASON_LABELS = {
  overdue: "просрочено",
  hold: "пауза",
  "no-assignee": "нет исполнителя",
  "no-story-points": "нет story points",
  "no-due-date": "нет срока",
  "high-priority-queue": "высокий приоритет в очереди",
  "too-old": "слишком старая",
  "shorter-than-min-stay": "короче минимального пребывания",
  "no-timing": "нет тайминга",
};

export const ATTENTION_ROLES = new Set(["hold", "canceled"]);
export const ATTENTION_SCOPE = new Set(["added", "removed"]);

export function reasonLabel(reason) {
  if (reason == null) {
    return "";
  }
  return REASON_LABELS[reason] ?? reason;
}
