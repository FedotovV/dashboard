"""Один проход: collect, затем build. Экран этот модуль не вызывает."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dashboard.orchestrator.build import BuildRequest, BuildResult, build
from dashboard.orchestrator.collect import CollectRequest, collect


@dataclass
class RunRequest:
    team_path: Path
    source: Path
    out_dir: Path
    bundle_path: Path | None = None
    edits_path: Path | None = None
    manifest_path: Path | None = None
    accept_recompute: bool = False


def run(request: RunRequest) -> BuildResult:
    bundle_path = request.bundle_path or (request.out_dir / "_collect" / "canonical.json")
    collected = collect(CollectRequest(request.team_path, request.source, bundle_path))
    if collected.code != 0:
        return BuildResult(collected.code, collected.message)
    return build(
        BuildRequest(
            team_path=request.team_path,
            bundle_path=bundle_path,
            out_dir=request.out_dir,
            edits_path=request.edits_path,
            manifest_path=request.manifest_path,
            accept_recompute=request.accept_recompute,
        )
    )
