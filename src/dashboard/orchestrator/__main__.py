"""CLI сборки. Экран эту команду не вызывает."""

from __future__ import annotations

import argparse
from pathlib import Path

from dashboard.orchestrator.build import BuildRequest, build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать снимок дашборда из canonical JSON")
    parser.add_argument("--team", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--edits", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--accept-recompute", action="store_true")
    args = parser.parse_args(argv)
    result = build(
        BuildRequest(
            team_path=args.team,
            bundle_path=args.bundle,
            out_dir=args.out,
            edits_path=args.edits,
            manifest_path=args.manifest,
            accept_recompute=args.accept_recompute,
        )
    )
    print(result.message)
    return result.code


if __name__ == "__main__":
    raise SystemExit(main())
