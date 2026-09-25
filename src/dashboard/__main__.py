"""Один процесс: collect, build, serve. Кнопки сборки на экране нет."""

from __future__ import annotations

import argparse
from pathlib import Path

from dashboard.api.__main__ import main as serve_main
from dashboard.api.serve import ServeError, make_server, require_localhost
from dashboard.orchestrator.__main__ import main as build_main
from dashboard.orchestrator.collect import CollectRequest, collect
from dashboard.orchestrator.run import RunRequest, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dashboard", description="Собрать слепок и открыть его на localhost")
    commands = parser.add_subparsers(dest="command", required=True)

    collect_parser = commands.add_parser("collect", help="fixture или file → canonical JSON")
    collect_parser.add_argument("--team", type=Path, required=True)
    collect_parser.add_argument("--source", type=Path, required=True)
    collect_parser.add_argument("--bundle", type=Path, required=True)

    build_parser = commands.add_parser("build", help="canonical JSON → слепок")
    build_parser.add_argument("--team", type=Path, required=True)
    build_parser.add_argument("--bundle", type=Path, required=True)
    build_parser.add_argument("--out", type=Path, required=True)
    build_parser.add_argument("--edits", type=Path)
    build_parser.add_argument("--manifest", type=Path)
    build_parser.add_argument("--accept-recompute", action="store_true")

    serve_parser = commands.add_parser("serve", help="экраны на 127.0.0.1")
    serve_parser.add_argument("--snapshots", type=Path, required=True)
    serve_parser.add_argument("--team", required=True)
    serve_parser.add_argument("--edits", type=Path, default=None)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--date", default=None)

    run_parser = commands.add_parser("run", help="collect и build, по флагу ещё serve")
    run_parser.add_argument("--team", type=Path, required=True)
    run_parser.add_argument("--source", type=Path, required=True)
    run_parser.add_argument("--out", type=Path, required=True)
    run_parser.add_argument("--bundle", type=Path)
    run_parser.add_argument("--edits", type=Path)
    run_parser.add_argument("--manifest", type=Path)
    run_parser.add_argument("--accept-recompute", action="store_true")
    run_parser.add_argument("--serve", action="store_true")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8765)
    run_parser.add_argument("--date", default=None)

    args = parser.parse_args(argv)
    if args.command == "collect":
        result = collect(CollectRequest(args.team, args.source, args.bundle))
        print(result.message)
        return result.code
    if args.command == "build":
        forwarded = ["--team", str(args.team), "--bundle", str(args.bundle), "--out", str(args.out)]
        if args.edits:
            forwarded.extend(["--edits", str(args.edits)])
        if args.manifest:
            forwarded.extend(["--manifest", str(args.manifest)])
        if args.accept_recompute:
            forwarded.append("--accept-recompute")
        return build_main(forwarded)
    if args.command == "serve":
        forwarded = ["--snapshots", str(args.snapshots), "--team", args.team, "--host", args.host, "--port", str(args.port)]
        if args.edits:
            forwarded.extend(["--edits", str(args.edits)])
        if args.date:
            forwarded.extend(["--date", args.date])
        return serve_main(forwarded)
    try:
        if args.serve:
            require_localhost(args.host)
    except ServeError as exc:
        print(exc)
        return 2
    result = run(
        RunRequest(
            team_path=args.team,
            source=args.source,
            out_dir=args.out,
            bundle_path=args.bundle,
            edits_path=args.edits,
            manifest_path=args.manifest,
            accept_recompute=args.accept_recompute,
        )
    )
    print(result.message)
    if result.code != 0 or not args.serve:
        return result.code
    server = make_server(args.out, _team_id(result.path), args.host, args.port, args.date, args.edits)
    if args.date:
        print(f"http://{args.host}:{args.port}/?date={args.date}")
    else:
        print(f"http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


def _team_id(snapshot: Path | None) -> str:
    if snapshot is None:
        return ""
    return snapshot.parent.name


if __name__ == "__main__":
    raise SystemExit(main())
