"""Локальный экран. Сборку не запускает."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dashboard.api.serve import ServeError, make_server, require_bind, token_from_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Открыть экраны «Спринт» и «Период» на localhost")
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--edits", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--date", default=None)
    parser.add_argument("--token-env", default=None)
    args = parser.parse_args(argv)
    token = token_from_env(args.token_env, os.environ)
    try:
        require_bind(args.host, token)
    except ServeError as exc:
        print(exc)
        return 2
    server = make_server(
        args.snapshots,
        args.team,
        args.host,
        args.port,
        args.date,
        args.edits,
        args.config,
        args.manifest,
        token,
    )
    if args.date:
        print(f"http://{args.host}:{args.port}/?date={args.date}")
    else:
        print(f"http://{args.host}:{args.port}/")
    if args.config is not None:
        print(f"http://{args.host}:{args.port}/setup")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
