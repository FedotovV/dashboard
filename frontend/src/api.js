export async function loadSprint() {
  const response = await fetch("/api/sprint");
  const text = await response.text();
  if (!response.ok) {
    throw new Error(text.trim() || "слепок не открылся");
  }
  return JSON.parse(text);
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
