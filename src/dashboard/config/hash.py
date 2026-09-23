"""Хеши правил. Общий хеш включает версии формул, которые умеет движок."""

from __future__ import annotations

import hashlib
import json

from dashboard.config.model import TeamConfig

FORMULA_VERSIONS = {
    "blockers": 1,
    "burndown": 1,
    "classification": 1,
    "completionVsCommitted": 1,
    "cycleTime": 1,
    "hygiene": 1,
    "personLoad": 1,
    "projectList": 1,
    "scopeChange": 1,
    "sprintFlow": 1,
    "statusHours": 1,
    "waitTime": 1,
}


def canonical_dumps(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(data: object) -> str:
    return hashlib.sha256(canonical_dumps(data).encode("utf-8")).hexdigest()


def input_hashes(config: TeamConfig) -> dict[str, str]:
    return {
        "calendar": digest(config.raw_calendar),
        "workflow": digest(config.raw_workflow),
        "taxonomy": digest(config.raw_taxonomy),
        "scope": digest(config.raw_scope),
    }


def rule_hash(config: TeamConfig) -> str:
    return digest(
        {
            "calendar": config.raw_calendar,
            "workflow": config.raw_workflow,
            "taxonomy": config.raw_taxonomy,
            "scope": config.raw_scope,
            "formulas": FORMULA_VERSIONS,
        }
    )
