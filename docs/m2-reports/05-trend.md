# Отчёт. Шаг 5. Тренд

## Что проверялось

После `build` `scope-days` с положенной рядом историей спарклайн содержит 2026-09-10 и 2026-09-14 и не содержит 2026-09-11. Бейдж прошлого спринта `s-prev` есть. Без объекта `previous` бейдж не рисуется и нули прошлого потока не подставляются.

## Команда

```bash
python3 -m pytest tests/test_sprint_page.py::test_scope_days_shows_composition_flow_and_trend tests/test_sprint_page.py::test_incomplete_membership_does_not_invent_scope -q
```

## Результат

2 теста, все прошли.
