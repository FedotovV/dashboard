"""Объект метрики снимка и текст «Как считается»."""

from __future__ import annotations

from dataclasses import dataclass, field


TEMPLATES = {
    "cycleTime": (
        "Медиана рабочих дней в роли active до закрытия. "
        "Интервал короче {minStaySeconds} с в сумму не входит. Версия 1."
    ),
    "waitTime": (
        "Медиана рабочих дней в роли wait до закрытия. "
        "Интервал короче {minStaySeconds} с в сумму не входит. Версия 1."
    ),
    "sprintFlow": "Счётчики текущего состава по ролям статусов. Версия 1.",
    "scopeChange": "Состав на старте дня спринта, добавленные и снятые. Версия 1.",
    "completionVsCommitted": (
        "Сделанное среди состава на старте. Отменённые остаются в знаменателе. Версия 1."
    ),
    "hygiene": "Одна плашка качества данных на задачу. Это не рейтинг. Версия 1.",
    "blockers": "Список причин. Балла риска нет. Версия 1.",
    "personLoad": (
        "Задачи текущего состава по людям, включая нули. "
        "Бэклог, работа, пауза, тест и завершение — роли statusMap. Версия 1."
    ),
    "burndown": (
        "Линия от story points на момент входа. "
        "Ось дней без выходных и праздников. Версия 1."
    ),
    "classification": (
        "Голова эпика важнее метки. Без головы и без явной метки — unknown. "
        "Порог плашки {unknownWarnPct}%. Версия 1."
    ),
    "statusHours": (
        "Часы в статусе, не списание. Номинал дня {nominalSeconds} с. Версия 1."
    ),
    "projectList": "Эпики из taxonomy. Релиз и заметка берутся из правок. Версия 1.",
}


class _Params(dict):
    def __missing__(self, key: str) -> str:
        return ""


def explain(metric_id: str, params: dict) -> str:
    return TEMPLATES[metric_id].format_map(_Params(params))


@dataclass
class Metric:
    id: str
    unit: str
    value: float | None
    population: list[str] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    detail: dict | None = None
    version: int = 1
    explain: str = ""

    def __post_init__(self) -> None:
        if not self.explain:
            self.explain = explain(self.id, self.params)

    def to_json(self) -> dict:
        payload = {
            "id": self.id,
            "version": self.version,
            "unit": self.unit,
            "value": self.value,
            "population": list(self.population),
            "excluded": list(self.excluded),
            "warnings": list(self.warnings),
            "params": self.params,
            "explain": self.explain,
        }
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload
