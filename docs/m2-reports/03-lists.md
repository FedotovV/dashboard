# Отчёт. Шаг 3. Блокеры, люди, таблица

## Что проверялось

Человек `idle` с пустым списком остаётся на экране. Блокеры идут в порядке слепка: просрочка раньше паузы. Колонка story points скрыта, когда поле SP выключено. В таблице нет пятёрки из bundle, которую движок в снимок не положил.

## Команда

```bash
python3 -m pytest tests/test_sprint_page.py::test_empty_person_stays_and_blockers_keep_snapshot_order tests/test_sprint_page.py::test_no_points_hides_burndown_and_story_point_column -q
```

## Результат

2 теста, все прошли.
