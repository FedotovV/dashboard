import { useEffect, useState } from "react";
import { loadSprint } from "./api.js";
import { SprintScreen } from "./SprintScreen.jsx";
import { applyTheme, readTheme } from "./theme.js";

export function App() {
  const [theme, setTheme] = useState(readTheme);
  const [screen, setScreen] = useState("sprint");
  const [sprint, setSprint] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    let active = true;
    loadSprint()
      .then((payload) => {
        if (active) {
          setSprint(payload);
        }
      })
      .catch((exc) => {
        if (active) {
          setError(exc.message || "слепок не открылся");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const teamId = sprint?.teamId || "";
  return (
    <div className="app">
      <aside>
        <p className="brand">
          {teamId || "Команда"}
          <small>дашборд команды</small>
        </p>
        <nav>
          <ScreenButton current={screen} id="sprint" onSelect={setScreen}>Спринт</ScreenButton>
          <ScreenButton current={screen} id="period" onSelect={setScreen}>Период</ScreenButton>
          <ScreenButton current={screen} id="setup" onSelect={setScreen}>Настройка</ScreenButton>
        </nav>
        <div className="themes" role="group" aria-label="Тема">
          <ThemeButton theme={theme} id="light" onTheme={setTheme}>Светлая</ThemeButton>
          <ThemeButton theme={theme} id="dark" onTheme={setTheme}>Тёмная</ThemeButton>
        </div>
      </aside>
      <main>
        {screen === "sprint" ? <SprintScreen sprint={sprint} error={error} /> : null}
        {screen === "period" ? <Later title="Период" /> : null}
        {screen === "setup" ? <Later title="Настройка" /> : null}
        <p className="foot">Числа из слепка. Сборка с этого экрана не запускается.</p>
      </main>
    </div>
  );
}

function ScreenButton({ current, id, onSelect, children }) {
  const on = current === id;
  return (
    <button type="button" className={on ? "on" : ""} aria-current={on ? "page" : undefined} onClick={() => onSelect(id)}>
      {children}
    </button>
  );
}

function ThemeButton({ theme, id, onTheme, children }) {
  const on = theme === id;
  return (
    <button type="button" className={on ? "on" : ""} aria-pressed={on} onClick={() => onTheme(id)}>
      {children}
    </button>
  );
}

function Later({ title }) {
  return (
    <div className="top">
      <div>
        <h1>{title}</h1>
        <p className="sub">Экран ещё не собран.</p>
      </div>
    </div>
  );
}
