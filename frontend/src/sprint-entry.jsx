import { renderToStaticMarkup } from "react-dom/server";
import { SprintScreen } from "./SprintScreen.jsx";

export function renderSprint(view) {
  return renderToStaticMarkup(<SprintScreen sprint={view} error="" />);
}
