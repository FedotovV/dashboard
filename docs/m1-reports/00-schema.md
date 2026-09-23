# Отчёт. Шаг 0. Схема снимка

## Что проверялось

Схема снимка принимает `dueDate`, `closedBeforeDue`, `detail`, `explain`, `trend` и хеш `bundle`. Пример без хеша bundle не проходит. `breakStart` внутри окна допустим, перерыв за пределами окна — нет. Старые примеры без `breakStart` остаются валидны.

## Команды

```bash
python3 scripts/check_contracts.py
python3 -m pytest tests/test_schema.py -q
```

## Результат

`contracts ok`. 9 тестов, все прошли. Движок в этом шаге не запускался.
