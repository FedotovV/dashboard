import { num } from "../format.js";

export function Figure({ value, attention = false }) {
  if (attention) {
    return <span className="num" data-attention="true">{num(value)}</span>;
  }
  return <span className="num">{num(value)}</span>;
}
