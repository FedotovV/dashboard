# Отчёт. Шаг 2. Состав, поток, цикл

## Что проверялось

`scope-days`: committed 2, added 1, removed 1, canceled 1, завершение «1 из 2». Фразы «всего минус старт» нет. При неполном membership числа состава — прочерк, не ноль.

`cycle-reopen`: в карточке цикла один раз есть 900 из текста слепка и секунды 14400. Второй формулы на странице нет.

## Команда

```bash
python3 -m pytest tests/test_sprint_page.py::test_scope_days_shows_composition_flow_and_trend tests/test_sprint_page.py::test_cycle_reopen_shows_explain_and_stored_seconds tests/test_sprint_page.py::test_incomplete_membership_does_not_invent_scope -q
```

## Результат

3 теста, все прошли.
