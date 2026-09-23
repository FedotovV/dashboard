"""Единственная арифметика рабочего времени."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dashboard.config.model import Calendar


def nominal_seconds(calendar: Calendar) -> int:
    return int(round(calendar.hours_per_day * 3600))


def is_workday(day: date, calendar: Calendar) -> bool:
    if day in calendar.holidays:
        return False
    if day in calendar.extra_workdays:
        return True
    return day.isoweekday() in calendar.workdays


def local_date(instant: datetime, timezone: str) -> date:
    return _aware(instant).astimezone(ZoneInfo(timezone)).date()


def elapsed_workdays(
    period_start: date,
    period_end: date,
    as_of: datetime,
    calendar: Calendar,
) -> list[date]:
    """Рабочие дни, у которых workEnd уже наступил к asOf."""
    tz = ZoneInfo(calendar.timezone)
    local_as_of = _aware(as_of).astimezone(tz)
    days: list[date] = []
    day = period_start
    while day <= period_end and day <= local_as_of.date():
        if is_workday(day, calendar):
            window_end = datetime.combine(day, calendar.work_end, tzinfo=tz)
            if local_as_of >= window_end:
                days.append(day)
        day += timedelta(days=1)
    return days


def work_seconds(start: datetime, end: datetime, calendar: Calendar) -> int:
    """Секунды пересечения [start, end) с рабочими окнами. Квант — секунда."""
    start = _aware(start)
    end = _aware(end)
    if end <= start:
        return 0
    tz = ZoneInfo(calendar.timezone)
    start = start.astimezone(tz)
    end = end.astimezone(tz)
    total = 0
    day = start.date()
    while day <= end.date():
        if is_workday(day, calendar):
            for window_start, window_end in _windows(day, calendar, tz):
                left = max(start, window_start)
                right = min(end, window_end)
                if right > left:
                    total += int(round((right - left).total_seconds()))
        day += timedelta(days=1)
    return total


def _windows(day: date, calendar: Calendar, tz: ZoneInfo):
    start = datetime.combine(day, calendar.work_start, tzinfo=tz)
    end = datetime.combine(day, calendar.work_end, tzinfo=tz)
    if calendar.break_minutes <= 0 or calendar.break_start is None:
        yield start, end
        return
    break_start = datetime.combine(day, calendar.break_start, tzinfo=tz)
    break_end = break_start + timedelta(minutes=calendar.break_minutes)
    if break_start > start:
        yield start, break_start
    if break_end < end:
        yield break_end, end


def _aware(instant: datetime) -> datetime:
    if instant.tzinfo is None:
        return instant.replace(tzinfo=ZoneInfo("UTC"))
    return instant


def clock(hour: int, minute: int = 0) -> time:
    return time(hour, minute)
