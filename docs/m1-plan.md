# M1. Движок

Первый шаг реализации. M0 закрыт: схемы, каталог, гид и `scripts/check_contracts.py` уже в репозитории. Экран не начинаем, пока золотые пары «каноника → снимок» не зелёные. Иначе форма зашитого JSON станет второй спецификацией.

Схема модулей: [architecture.html](architecture.html). Формулы: [metric-catalog.md](metric-catalog.md). Границы продукта: [plan.md](plan.md). Порядок кода, тестов и отчётов: [m1-implementation.md](m1-implementation.md). Релиз-ноутсы: [m1-release-notes.md](m1-release-notes.md).

## Выход шага

- Золотые случаи из раздела ниже зелёные.
- Текст «Как считается» показывает параметры той фикстуры, на которой посчитан снимок.
- Повторный `build` не меняет байты уже записанного слепка.
- `edits.json` после `build` байт-в-байт тот же.
- Смена `statusMap` без явной приёмки останавливает `build`, файлов слепка не появляется.
- `python3 scripts/check_contracts.py` печатает `contracts ok`.

## Что в этом шаге не появляется

Каталоги `connectors`, `api`, `web`. Команды `collect` и `serve`. Docker. `PUT /api/edits`. Новая версия формулы. Confluence, мессенджер, GitLab, вторая команда, SSO, кнопка пересборки на экране.

Коннектора нет: оркестратор читает готовый canonical JSON. Живой Jira — M5.

## Граница импортов

| Модуль | Может импортировать | Не импортирует |
| --- | --- | --- |
| `config` | схему и YAML | metrics, snapshotstore, edits |
| `metrics` | типы config, уже разобранные | файлы, сеть, snapshotstore, edits |
| `edits` | результат metrics | Jira, формулы |
| `snapshotstore` | схему снимка | пересчёт |
| `orchestrator` | все четыре | внутреннюю арифметику: вызывает `compute`, не копирует её |

История для бейджа и спарклайна — аргумент `compute`. Функция метрик каталог слепков не открывает. Открывает его оркестратор и передаёт объект.

## Срез 0. Снимок до кода движка

Каталог уже обещает факты, которым в `snapshot.schema.json` нет поля. Их добавляем до первой фикстуры, вместе с примером и проверкой контракта. Смысл каноники не меняем.

В `schema/snapshot.schema.json`:

- У задачи спринта необязательная `dueDate` (`string` дата или `null`). Колонка срока уже обещана каталогом; просрок по-прежнему причина блокера, отдельного виджета due нет.
- У метрики необязательный объект `detail`. Ключи свои у каждой формулы, см. таблицу ниже. Схема `detail` свободная: набор фиксирует золотой тест, не гигантский `oneOf`.
- У `sprint` необязательный `trend`:
  - `previous` — `null` или `{snapshotId, sprintId, byRole}`, где `byRole` повторяет счётчики `sprintFlow`;
  - `sparkline` — массив `{date, done}` только по дням, где слепок реально есть. Дыры не заполняются.
- В `inputHashes` поле `bundle`: хеш канонического JSON. Рядом остаются `calendar`, `workflow`, `taxonomy`, `scope`.

В `schema/team.schema.json` необязательный `calendar.breakStart` (`HH:MM`). Если поля нет, перерыв — один непрерывный промежуток по центру `[workStart, workEnd)`, целиком внутри окна. Существующие примеры без поля остаются валидны.

В каталог, без смены версии формул, две уточняющие фразы:

- Перерыв вырезается из окна так, как сказано выше. Вторая арифметика «вычесть минуты пропорционально» не используется.
- Интервал короче `minStaySeconds` в сумму цикла не входит. Ключ попадает в `excluded` с причиной `shorter-than-min-stay` только если после отбрасывания таких интервалов у задачи не осталось времени в роли `active`. Если длинный интервал есть, ключ в `population`.

`schema/examples/snapshot.example.json` обновляется под новую схему. `scripts/check_contracts.py` остаётся зелёным.

### Что лежит в `value` и в `detail`

`value` — ведущее число карточки. `null` не заменяется нулём. Остальные числа карточки — в `detail`.

| id | value | detail |
| --- | --- | --- |
| `cycleTime` | медиана рабочих дней | `perIssue`: ключ и секунды, вошедшие в сумму |
| `waitTime` | то же для роли `wait` | `perIssue` |
| `sprintFlow` | всего в текущем составе | `byRole`: active, wait, hold, queue, done, canceled |
| `scopeChange` | `null` | `committed`, `added`, `removed`; при неполном membership все три `null` |
| `completionVsCommitted` | done / committed | `done`, `committed` |
| `hygiene` | число задач с плашкой | `items`: ключ и одна причина |
| `blockers` | число задач в списке | `items`: ключ и причины в порядке каталога |
| `personLoad` | число людей в списке | `rows`: id, открытые ключи; нули остаются |
| `burndown` | остаток SP или `null` | `points`: date, ideal, actual по `storyPointsAtAdd` |
| `classification` | `unknownPct` | `paths`: ключ, headId или `null`, category, reason `head\|rule\|label\|unknown` |
| `statusHours` | `statusTimeRatio` или `null` | `parallelism`, `inheritedSeconds`, `ownSeconds`, `days` человека до масштаба и после |
| `projectList` | число эпиков | `rows`: ключ, имя, статус, feature lead; релиз и заметку дописывает edits |

Единица цикла и ожидания — `workdays`: `value = секунды / nominalSeconds`. Округление до 2 знаков делает подпись экрана, не движок. Золотой тест сверяет целые секунды в `detail`.

Покрытие — не метрика-карточка, а объект `coverage` снимка: `timing`, `unknownPct`, `storyPoints` (`off|partial|full`), `assigneeMatchPct`, `membership`.

## Срез 1. Конфиг и время

Появляется `pyproject.toml` с зависимостями разработки (`pyyaml`, `jsonschema`, `pytest`), `pythonpath = src` и каталог `src/dashboard`. Python 3.11, часовые пояса из `zoneinfo`.

`config.load_team(path) -> TeamConfig`

- читает YAML, проверяет `team.schema.json`;
- отклоняет неизвестную `catalogVersion` и неизвестную `metrics.<id>.version`;
- отклоняет окно, у которого `(workEnd − workStart) − breakMinutes` не равно `hoursPerDay`;
- секретов в объекте нет: `authEnv` остаётся именем переменной.

`config.input_hashes(config)` и `config.rule_hash(config)` — SHA-256 от канонического JSON (`sort_keys`, без лишних пробелов, UTF-8). Четыре отдельных хеша и один общий. Общий включает версии формул из каталога, которые движок умеет считать (все v1).

`metrics.time.work_seconds(start, end, calendar) -> int`

- инстанты в UTC, дата режется только в `calendar.timezone`;
- рабочий день — `workdays` или `extraWorkdays`, и не `holidays`;
- окно `[workStart, workEnd)` минус один перерыв;
- полуинтервалы; верхняя граница, заданная датой, — `workEnd` этой даты;
- квант — секунды, без `floor` по часам.

Золото среза, ещё без полного снимка: праздник не копится; extra workday копится; 60 минут `breakStart` не входят в пересечение; полночь UTC не равна полуночи команды.

## Срез 2. Цикл и срок

`cycleTime` и `waitTime` версии 1. Цикл — сумма `work_seconds` по интервалам роли `active` до первого входа в `terminal`, не спан от первого входа до закрытия. Возврат в очередь между заходами в сумму не входит. `waitTime` — та же функция на роли `wait`.

Выход из `terminal` снимает запечатку: если manifest помечал задачу закрытой, а текущая роль уже не `terminal`, секунды считаются заново по `statusChanges` bundle. Код запечатки не подменяет историю фикстуры.

Due сравнивается как календарная дата в зоне команды. «Раньше срока» — дата закрытия строго раньше `dueDate`. Закрытие в 00:30 локального дня срока — не раньше срока.

Фикстура зоны `Europe/Moscow`:

- `resolutionAt = 2026-09-09T20:30:00Z` → локально 2026-09-09 23:30, due `2026-09-10` → раньше срока;
- `resolutionAt = 2026-09-09T21:30:00Z` → локально 2026-09-10 00:30, тот же due → не раньше срока.

Короткий заход: пребывание 10 минут при `minStaySeconds = 900` в сумму не входит.

## Срез 3. Состав спринта

В состав входят задачи, у которых `removedAt` пуст, тип входит в `scope.issueTypes`, проект входит в `scope.projectKeys` (если список задан), и `subtask = false`, когда `countSubtasks = false`.

`sprintFlow` считает роли текущего состава. `done` — `terminal` и outcome `completed` (пустое outcome = completed). `canceled` — `terminal` и outcome `canceled`. Отменённая остаётся в знаменателе `completionVsCommitted` и не входит в числитель.

`scopeChange`: `committed` — `addedAt` не позже начала `sprint.start` в зоне команды и задача всё ещё в составе; `added` — позже старта и не снята; `removed` — `removedAt` задан. Нет `addedAt` ни у одной задачи состава → `coverage.membership = incomplete`, все три числа `null`. Вычитать «сейчас минус старт» нельзя.

Золото: add на день 3, remove на день 7 дают разные ключи в `added` и `removed`.

## Срез 4. Классификация

Рёбра — `taxonomy.linkTypes` и epic link. `fromId` — родитель, `toId` — потомок. `Blocks` ребром не является. Обход вниз от `taxonomy.epics`, циклы обрываются. Ничья двух голов одной глубины: раньше в `taxonomy.priority`, затем меньший id родителя.

Порядок решения, как в каталоге: голова дерева → первое совпавшее `rules[]` → `prodLabel` → `techLabel` → `unknown`. Метка tech не перебивает проектную голову. Задача без головы не становится технической.

Золото одним bundle:

- ромб: две головы одной глубины, побеждает категория раньше в `priority`;
- цикл ссылок не зацикливает обход;
- метка tech на задаче с проектной головой → категория головы;
- задача без головы, без правила и без метки → `unknown`, путь с `reason = unknown`.

## Срез 5. Часы в статусе

Подпись смысла — «часы в статусе, не списание». В именах полей слова utilization нет.

Сырые секунды человека за день — сумма `work_seconds` его задач с ролью `active`. Если сумма больше `nominalSeconds × allocation`, категории этого дня умножаются на предел / сумму. Масштаб после разложения по задачам, затем суммы. Доля inherited не зависит от порядка округления.

`inherited` — секунды периода у задач, чей первый `active` раньше `period.start`. `own = scaled − inherited`. `capacity` — сумма по прошедшим рабочим дням. `statusTimeRatio = scaled / capacity`. `parallelism = raw / scaled`.

Прошедших рабочих дней 0 → `statusTimeRatio` и `parallelism` равны `null`. Это и есть «метрики темпа» v1: прогноза «успеем ли» в каталоге нет.

Золото: два тикета одного человека в один день, сырая сумма больше номинала, один тикет начат до периода, второй внутри. В `detail.days` видны секунды до масштаба и после.

## Срез 6. Остальные карточки

- `hygiene` — одна причина на задачу, порядок причин как в каталоге. Пустой исполнитель не дублируется. Просроченный due — не гигиена.
- `blockers` — список, не балл. Порядок: просроченное обязательство, затем hold, затем пустой исполнитель на `active`.
- `personLoad` — все `members`, у кого `asOf` внутри `[activeFrom, activeTo]` и не внутри `absences`. Ноль открытых задач строку не убирает.
- `burndown` только при `coverage.storyPoints = full`: поле SP задано и у каждой задачи состава есть `storyPointsAtAdd`. Идеал и факт идут от `storyPointsAtAdd`. Текущая оценка, изменённая после входа, линию не двигает. Поля SP нет → `coverage.storyPoints = off`, `value = null`.
- `projectList` — строки эпиков из `taxonomy.epics`. Чужой id в правках даёт warning и не исчезает. Пустой список эпиков — warning, не выдуманные строки.
- `assigneeMatchPct` — доля задач с исполнителем, чей id совпал с человеком команды. Cloud матчится по `jiraAccountId`, Server — по `jiraUsername`. Несовпавшие в ёмкость не входят и видны в `statusHours` отдельной пометкой «вне состава».

## Срез 7. Сборка

`edits.apply(computed, edits)` дописывает релиз и заметку в строки `projectList`. Неизвестный `epicId` → warning на метрике. Функция файл не открывает.

`snapshotstore.write_snapshot(document, dest)` проверяет документ схемой и создаёт файл. Если путь занят, файл на запись не открывается. Сравнение делает оркестратор: считает документ в памяти.

Имя файла: `{out}/{teamId}/{YYYY-MM-DD}.json`. Дата — `asOf` в зоне команды, не в зоне машины. `snapshotId` тот же: `{teamId}-{YYYY-MM-DD}`. Повтор того же дня попадает в тот же путь.

`orchestrator.build(request) -> BuildResult` делает только это, по порядку:

1. Загрузить и проверить team. Ошибка схемы или инварианта → код 2, файлов нет.
2. Посчитать хеши. Если manifest есть и `ruleHash` другой, а `accept_recompute` ложь → код 3, слепок не пишется, edits не трогается.
3. Прочитать canonical JSON, проверить `canonical.schema.json`.
4. Прочитать edits, запомнить байты, проверить схему.
5. Собрать `history` из уже лежащих слепков этого `teamId`.
6. `compute`. Если задача в manifest была `terminal`, а сейчас роль иная — в расчёт идёт история bundle, не запечатанные секунды.
7. `apply`.
8. Собрать документ снимка, проверить `snapshot.schema.json`.
9. Если файла дня нет — записать. Если есть и байты совпали — код 0, файл не открывать на запись. Если есть и байты разошлись — код 4, старые байты на месте.
10. Сверить байты edits с шагом 4.
11. При `accept_recompute` записать manifest с новым хешем и пустым `timings`. Запечатанные тайминги смену карты статусов не переживают.

Команда разработчика:

```bash
python -m dashboard.orchestrator.build \
  --team fixtures/m1/<case>/team.yaml \
  --bundle fixtures/m1/<case>/canonical.json \
  --edits fixtures/m1/<case>/edits.json \
  --manifest fixtures/m1/<case>/manifest.json \
  --out var/snapshots
```

`--accept-recompute` существует для шага 11. Экран его не вызывает.

Текст «Как считается» — шаблон рядом с формулой, в него подставляются фактические `params` (например `minStaySeconds` из yaml фикстуры). Шаблон не парсит весь каталог. Тест проверяет, что в тексте есть число из yaml этого случая и что версия метрики равна 1, как в каталоге.

## Золотые пары

Каждый случай — каталог `fixtures/m1/<case>/` с `team.yaml`, `canonical.json` и `expected.snapshot.json`. Ожидаемый снимок пишется по каталогу вручную и сам проходит `snapshot.schema.json`. Копировать его из прогона движка нельзя: так фиксируется ошибка формулы.

Общий календарь случаев, если случай не про другое: `Europe/Moscow`, пн–пт, 10:00–19:00, перерыв 60 минут с `breakStart: "14:00"`, `hoursPerDay: 8`.

| Случай | Что обязано сойтись |
| --- | --- |
| `due-midnight` | Два закрытия по разные стороны полуночи Москвы, см. срез 2 |
| `cycle-reopen` | Короткий заход выпал; очередь между двумя `active` не в сумме; после выхода из terminal цикл посчитан заново |
| `parallel-day` | Два тикета, масштаб дня, inherited и own в одном дне |
| `classify` | Ромб, цикл связей, метка поверх головы, голова отсутствует → unknown |
| `scope-days` | Add на день 3, remove на день 7; canceled в знаменателе completion и не в числителе |
| `no-points` | Поле SP выключено, burndown `null`, нулей SP в снимке нет |
| `points-moved` | `storyPoints` после входа изменились, линия burndown держится на `storyPointsAtAdd` |
| `pace-zero` | `asOf` в первый день, прошедших рабочих дней 0, темп `null` |
| `write-once` | Второй build, байты первого файла те же |
| `edits-intact` | После build байты `edits.json` те же, релиз виден в строке эпика |
| `rules-changed` | Другой `statusMap` при старом manifest → код 3, нового слепка нет |

`prevSprint` проверяется на `scope-days`: в history передан последний слепок прошлого спринта, в `trend.previous` его `byRole`. Отдельный день без слепка в `sparkline` не появляется.

## Порядок работы

Срезы 0–7 идут по очереди. Следующий не начинается, пока тесты предыдущего зелёные. Схема меняется только в срезе 0 и только вместе с примером и `check_contracts.py`.

Каталоги модулей создаются в том срезе, где у них появляется код: `config` и `metrics` в срезе 1, `edits` и `snapshotstore` и `orchestrator` в срезе 7. `connectors`, `api`, `web` в M1 не создаются.

Команды, когда файлы уже есть:

```bash
python3 scripts/check_contracts.py
python3 -m pytest
```

До появления `pytest` в репозитории его не вызывают.
