export async function loadSprint() {
  return readJson("/api/sprint");
}

export async function loadTeam() {
  return readJson("/api/team");
}

export async function saveEdit(fields) {
  const body = new URLSearchParams();
  for (const [key, value] of Object.entries(fields)) {
    if (value != null) {
      body.set(key, String(value));
    }
  }
  const response = await fetch("/api/edits", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(errorText(text) || "пометка не записалась");
  }
  return text;
}

async function readJson(url) {
  const response = await fetch(url);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(text.trim() || "слепок не открылся");
  }
  return JSON.parse(text);
}

function errorText(text) {
  const trimmed = text.trim();
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed?.error) {
      return parsed.error;
    }
  } catch {
    return trimmed;
  }
  return trimmed;
}

export function coverageNotes(coverage) {
  const notes = [];
  const timing = coverage?.timing;
  if (timing === "none" || timing === "partial") {
    notes.push(`Тайминги: coverage.timing = ${timing}`);
  }
  if (coverage?.membership === "incomplete") {
    notes.push("Состав: coverage.membership = incomplete");
  }
  return notes;
}
