export function num(value) {
  if (value == null || typeof value === "boolean") {
    return "—";
  }
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      return String(value);
    }
    return JSON.stringify(value);
  }
  return String(value);
}

export function duration(seconds) {
  if (!Number.isInteger(seconds)) {
    return `${num(seconds)} с`;
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const parts = [];
  if (hours) {
    parts.push(`${hours} ч`);
  }
  if (minutes) {
    parts.push(`${minutes} мин`);
  }
  if (parts.length === 0) {
    parts.push("0 мин");
  }
  return `${parts.join(" ")} (${seconds} с)`;
}

export function ratio(value) {
  if (typeof value === "boolean" || typeof value !== "number") {
    return num(value);
  }
  if (!Number.isInteger(value)) {
    return value.toFixed(2);
  }
  return num(value);
}

export function positive(value) {
  return typeof value === "number" && value > 0;
}
