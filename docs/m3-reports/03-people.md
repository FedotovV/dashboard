# Отчёт. Шаг 3. Люди и путь к голове

## Что сделано

На слепке `classify` у «Разработчик» виден ключ A-1, ссылка `https://jira.example.com/browse/A-1` и путь «голова p-1, проект». У U-1 путь «нет головы», строка выделена. Обход дерева экран не повторяет: путь берётся из `classification.detail.paths`.

## Команда

```bash
python3 -m pytest tests/test_period_page.py::test_unknown_banner_is_above_the_hours_ring_and_people_keep_the_path -q
```

## Результат

Тест прошёл.
