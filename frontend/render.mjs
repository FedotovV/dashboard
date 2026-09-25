import { build } from "esbuild";
import { createRequire } from "node:module";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const frontend = new URL(".", import.meta.url).pathname;
const dir = mkdtempSync(join(tmpdir(), "dash-render-"));
const outfile = join(dir, "screen.cjs");

await build({
  absWorkingDir: frontend,
  entryPoints: ["src/sprint-entry.jsx"],
  bundle: true,
  format: "cjs",
  platform: "node",
  jsx: "automatic",
  outfile,
  logLevel: "silent",
});

const mod = require(outfile);
const view = JSON.parse(readFileSync(0, "utf8"));
process.stdout.write(mod.renderSprint(view));
rmSync(dir, { recursive: true, force: true });
