"""Сборка золотого слепка для экрана. Страница сама build не вызывает."""

import shutil
from pathlib import Path

from dashboard.orchestrator.build import BuildRequest, build

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "m1"


def build_case(case: str, tmp_path: Path, *, history: bool = False) -> Path:
    source = FIXTURES / case
    out = tmp_path / case
    if history and (source / "history").exists():
        shutil.copytree(source / "history", out / "card")
    result = build(
        BuildRequest(
            team_path=source / "team.yaml",
            bundle_path=source / "canonical.json",
            out_dir=out,
        )
    )
    assert result.code == 0, result.message
    assert result.path is not None
    return result.path
