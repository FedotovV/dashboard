# Отчёт. Шаг 3. Состав спринта

## Что проверялось

Старт спринта 2026-09-07. Добавление 9 сентября — `added`, снятие 13 сентября — `removed`. Задачи, вошедшие в календарный день старта, остаются `committed`.

Текущий состав: один `active`, один `done`, один `canceled`, всего 3. Снятая задача в счётчики `sprintFlow` не входит.

`completionVsCommitted` = 1 / 2. Отменённая задача в знаменателе и не в числителе.

Пустой `addedAt` обнуляет committed, added и removed и ставит `coverage.membership = incomplete`.

## Команда

```bash
python3 -m pytest tests/test_flow.py -q
```

## Результат

2 теста, все прошли.
