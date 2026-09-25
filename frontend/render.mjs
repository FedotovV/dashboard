import { build } from "esbuild";
import { createRequire } from "node:module";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const frontend = new URL(".", import.meta.url).pathname;
const dir = mkdtempSync(join(tmpdir(), "dash-render-"));
const outfile = join(dir, "screen.cjs");

const screen = process.argv[2] || "sprint";
const entry = screen === "period" ? "src/period-entry.jsx" : "src/sprint-entry.jsx";
const exportName = screen === "period" ? "renderPeriod" : "renderSprint";

await build({
  absWorkingDir: frontend,
  entryPoints: [entry],
  bundle: true,
  format: "cjs",
  platform: "node",
  jsx: "automatic",
  outfile,
  logLevel: "silent",
});

const mod = require(outfile);
const view = JSON.parse(readFileSync(0, "utf8"));
process.stdout.write(mod[exportName](view));
rmSync(dir, { recursive: true, force: true });
