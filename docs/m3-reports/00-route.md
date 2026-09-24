# Отчёт. Шаг 0. Документ маршрута

## Что сделано

`GET /api/team` копирует из файла слепка `asOf`, покрытие, период, спарклайн, завершение к старту, людей и задачи. `compute` не вызывается. `GET /api/metrics/classification` и `statusHours` отдают версию, текст и параметры, без `value`. `riskScore` по-прежнему 404.

## Команда

```bash
python3 -m pytest tests/test_period_api.py -q
```

## Результат

3 теста, все прошли.
