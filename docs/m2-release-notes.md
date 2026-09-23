# Релиз-ноутс. M2. Экран «Спринт»

Веха M2. Страница читает слепок M1. Формулы не менялись. Экрана «Период» и записи правок нет.

## Сделано

- `GET /api/sprint` отдаёт один документ из файла слепка: момент, зона, покрытие, спринт, тренд.
- `GET /api/metrics/{id}` отдаёт версию, текст «Как считается» и параметры. Значения метрики в этом ответе нет.
- Экран показывает состав, поток, цикл и ожидание, блокеров, людей вместе с нулями, таблицу задач, burndown и тренд. Числа копируются из слепка.
- Нет SP — блока burndown нет и нулей story points нет. Нет `previous` — бейджа прошлого спринта нет.
- `python3 -m dashboard.api.serve` слушает только `127.0.0.1`. Кнопки сборки нет. `PUT` не принимается.

## Как открыть

```bash
python3 -m dashboard.orchestrator.build \
  --team fixtures/m1/scope-days/team.yaml \
  --bundle fixtures/m1/scope-days/canonical.json \
  --out var/snapshots
python3 -m dashboard.api.serve \
  --snapshots var/snapshots \
  --team card \
  --host 127.0.0.1 \
  --port 8765
```

Адрес: `http://127.0.0.1:8765/`.

Чтобы на `scope-days` был бейдж прошлого спринта, перед `build` скопируйте `fixtures/m1/scope-days/history/` в `var/snapshots/card/`.

Второй порт для слепка без SP: фикстура `fixtures/m1/no-points`, каталог `var/snapshots-no-points`, порт 8766.

## Не входит

Экран «Период», часы в статусе, классификация, список эпиков, `PUT /api/edits`, `collect`, Docker, живая Jira. Карточка утилизации, балл риска и цветовые пороги.

## Проверка

`python3 scripts/check_contracts.py` — `contracts ok`. `python3 -m pytest` — 81 тест. Отчёты — в `docs/m2-reports/`.
