# Отчёт. Шаг 4. Burndown

## Что проверялось

`points-moved`: блок есть, остаток 3, даты точек совпадают со слепком. `no-points`: блока нет и подписи «0 SP» нет.

## Команда

```bash
python3 -m pytest tests/test_sprint_page.py::test_points_moved_keeps_the_burndown_dates_from_the_snapshot tests/test_sprint_page.py::test_no_points_hides_burndown_and_story_point_column -q
```

## Результат

2 теста, все прошли.
