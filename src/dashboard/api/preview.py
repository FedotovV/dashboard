"""Сборка экрана из редактируемого JSON и раздача на localhost.

Каталог var/ui для этой команды заменяется: это песочница просмотра, не архив слепков.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from dashboard.api.serve import ServeError, make_server, require_localhost
from dashboard.orchestrator.build import BuildRequest, BuildResult, build

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = ROOT / "fixtures" / "ui" / "demo.json"
DEFAULT_WORK = ROOT / "var" / "ui"


def refresh(data_path: Path, work: Path) -> BuildResult:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    team = data["team"]
    team_id = team["team"]["id"]
    work.mkdir(parents=True, exist_ok=True)
    out = work / "snapshots"
    team_dir = out / team_id
    if team_dir.exists():
        shutil.rmtree(team_dir)
    team_dir.mkdir(parents=True)
    for item in data.get("history") or []:
        dest = team_dir / f"{item['date']}.json"
        dest.write_text(json.dumps(item["document"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    team_path = work / "team.json"
    bundle_path = work / "bundle.json"
    team_path.write_text(json.dumps(team, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bundle_path.write_text(json.dumps(data["bundle"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return build(BuildRequest(team_path=team_path, bundle_path=bundle_path, out_dir=out))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать экран из fixtures/ui/demo.json и открыть его")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-serve", action="store_true")
    args = parser.parse_args(argv)
    try:
        require_localhost(args.host)
    except ServeError as exc:
        print(exc)
        return 2
    result = refresh(args.data, args.work)
    print(result.message)
    if result.code != 0 or result.path is None:
        return result.code
    print(result.path)
    if args.no_serve:
        return 0
    team_id = json.loads(args.data.read_text(encoding="utf-8"))["team"]["team"]["id"]
    print(f"http://{args.host}:{args.port}/")
    server = make_server(args.work / "snapshots", team_id, args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
