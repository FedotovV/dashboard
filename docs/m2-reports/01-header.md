# Отчёт. Шаг 1. Шапка и плашка покрытия

## Что проверялось

Шапка берёт id спринта, даты и `asOf` из слепка, без пересчёта «сегодня». Плашка появляется при `coverage.timing = none` и при `membership = incomplete` и называет эти поля.

## Команда

```bash
python3 -m pytest tests/test_sprint_page.py::test_incomplete_membership_does_not_invent_scope tests/test_sprint_page.py::test_scope_days_shows_composition_flow_and_trend -q
```

## Результат

Оба теста прошли. На странице `scope-days` в шапке виден `asOf` файла `2026-09-14T16:00:00Z`.
