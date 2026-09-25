const KEY = "dashboard-theme";

export function readTheme() {
  const query = new URLSearchParams(window.location.search).get("theme");
  if (query === "light" || query === "dark") {
    return query;
  }
  const stored = localStorage.getItem(KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(KEY, theme);
}
