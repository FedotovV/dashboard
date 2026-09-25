export function browseHref(view, key) {
  const base = view?.jiraBaseUrl;
  if (typeof base !== "string" || !key) {
    return null;
  }
  const cleaned = base.trim().replace(/\/+$/, "");
  if (!cleaned.startsWith("https://") && !cleaned.startsWith("http://")) {
    return null;
  }
  return `${cleaned}/browse/${key}`;
}

export function metricOf(view, metricId) {
  const metrics = view?.sprint?.metrics || [];
  return metrics.find((item) => item?.id === metricId) ?? null;
}

export function periodMetric(view, metricId) {
  const metrics = view?.period?.metrics || [];
  return metrics.find((item) => item?.id === metricId) ?? null;
}
