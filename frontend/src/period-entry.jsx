import { renderToStaticMarkup } from "react-dom/server";
import { PeriodScreen } from "./PeriodScreen.jsx";

export function renderPeriod(view) {
  return renderToStaticMarkup(<PeriodScreen team={view} error="" />);
}
