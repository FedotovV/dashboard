"""Официальные нерабочие дни РФ на 2026 год для оси burndown.

Источник: статья 112 ТК РФ и постановление Правительства РФ
от 24.09.2025 № 1466. Переносы: суббота 3 января → пятница 9 января,
воскресенье 4 января → четверг 31 декабря. Праздник, попавший на
выходной, даёт следующий рабочий день: 8 марта (воскресенье) → 9 марта,
9 мая (суббота) → 11 мая. Сокращённые предпраздничные дни сюда не входят.
"""

from __future__ import annotations

from datetime import date, timedelta

from dashboard.config.model import Calendar

RU_NON_WORKING_2026 = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
        date(2026, 1, 9),
        date(2026, 2, 23),
        date(2026, 3, 8),
        date(2026, 3, 9),
        date(2026, 5, 1),
        date(2026, 5, 9),
        date(2026, 5, 11),
        date(2026, 6, 12),
        date(2026, 11, 4),
        date(2026, 12, 31),
    }
)


def chart_workday(day: date, calendar: Calendar) -> bool:
    """День оси burndown: без субботы, воскресенья и нерабочих дней.

    Праздник команды и официальный день РФ гасят день даже если он
    указан в extraWorkdays. extraWorkdays возвращает субботу или
    воскресенье, которые производственный календарь сделал рабочими.
    """
    if day in RU_NON_WORKING_2026 or day in calendar.holidays:
        return False
    if day in calendar.extra_workdays:
        return True
    if day.isoweekday() >= 6:
        return False
    return day.isoweekday() in calendar.workdays


def chart_days(start: date, end: date, calendar: Calendar) -> list[date]:
    days: list[date] = []
    day = start
    while day <= end:
        if chart_workday(day, calendar):
            days.append(day)
        day += timedelta(days=1)
    return days
