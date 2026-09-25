import { browseHref } from "../links.js";

export function IssueLink({ view, issueKey }) {
  const label = issueKey ?? "";
  const href = browseHref(view, issueKey);
  if (!href) {
    return label;
  }
  return <a href={href}>{label}</a>;
}
