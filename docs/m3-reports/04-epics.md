# Отчёт. Шаг 4. Эпики и завершение к старту

## Что сделано

Слепок `edits-intact` показывает релиз `2026-Q3` и заметку «Ждём макет». Пустой список эпиков — плашка, не таблица. Завершение на `scope-days` — ссылка «1 из 2» на экран спринта. При неполном membership дроби нет.

## Команда

```bash
python3 -m pytest tests/test_period_page.py::test_epic_note_and_committed_completion_come_from_the_snapshot tests/test_period_page.py::test_empty_epic_list_is_a_banner tests/test_period_page.py::test_incomplete_membership_hides_the_completion_fraction -q
```

## Результат

3 теста, все прошли.
