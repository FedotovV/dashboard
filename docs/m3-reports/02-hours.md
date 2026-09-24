# Отчёт. Шаг 2. Часы в статусе

## Что сделано

Кольцо строится из `inheritedSeconds` и `ownSeconds` слепка `parallel-day`: 14400 и 14400. День показывает 36000 с до масштаба и 28800 с после. Параллельность на экране `1.25`. Подпись — «часы в статусе, не списание». Доля к ёмкости без цветовой цели. При `coverage.timing = none` кольца нет и нулевая шкала не рисуется.

## Команда

```bash
python3 -m pytest tests/test_period_page.py::test_hours_ring_uses_snapshot_seconds tests/test_period_page.py::test_missing_timings_hide_the_ring -q
```

## Результат

2 теста, оба прошли. Слов utilization и «утилизац» в HTML нет.
