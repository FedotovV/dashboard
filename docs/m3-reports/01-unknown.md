# Отчёт. Шаг 1. Плашка unknown

## Что сделано

На `/period` плашка «Не разобрано» берёт процент из `classification.value` и порог из `params.unknownWarnPct`. В разметке слепка `classify` она стоит раньше блока часов. Доля заново не считается.

## Команда

```bash
python3 -m pytest tests/test_period_page.py::test_unknown_banner_is_above_the_hours_ring_and_people_keep_the_path -q
```

## Результат

Тест прошёл. В прогоне страницы плашка раньше `data-widget="hours"`, процент `33.333333333333336` пришёл из слепка.
