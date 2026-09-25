import { renderToStaticMarkup } from "react-dom/server";
import { SetupScreen } from "./SetupScreen.jsx";

export function renderSetup(view) {
  return renderToStaticMarkup(<SetupScreen view={view} error="" />);
}
