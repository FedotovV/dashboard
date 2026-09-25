# M4. Один процесс

M3 влит: оба экрана читают слепок, правки пишутся в свой файл. Этот шаг собирает bundle из фикстуры или файловой выгрузки и кладёт его в тот же `build`. Живая Jira, Docker и инкремент manifest не начинаются.

Формулы каталога не меняются. Версия метрик остаётся 1.

## Статус

- [x] План
- [x] Коннектор `fixture` — документ фикстуры без переписывания смысла
- [x] Коннектор `file` — выгрузка в канонику
- [x] `live` останавливается и сеть не открывается
- [x] `python -m dashboard`: `collect`, `build`, `serve`, `run`
- [x] Золото M1 одной командой
- [x] fileimport и прямой build ожидаемой каноники дают одни байты слепка
- [x] `GET /api/sprint` и `GET /api/team` сходятся с этими данными

Отчёт: [m4-reports/review.md](m4-reports/review.md).

## Команда

Режим берётся из `sources.mode`. Путь к сырью — аргумент, в YAML его нет.

```bash
python3 -m dashboard run \
  --team fixtures/m1/due-midnight/team.yaml \
  --source fixtures/m1/due-midnight/canonical.json \
  --out var/snapshots
```

Та же команда для выгрузки:

```bash
python3 -m dashboard run \
  --team fixtures/m4/file-sprint/team.yaml \
  --source fixtures/m4/file-sprint/raw \
  --out var/snapshots
```

`--serve` после успешного build открывает экраны на `127.0.0.1`. Другой адрес отвергается до collect. Кнопки сборки на экране нет.

Отдельные шаги: `collect --team --source --bundle`, `build` и `serve` с теми же флагами, что раньше.

`run` пишет canonical JSON в `--bundle` или в `{out}/_collect/canonical.json`, затем вызывает прежний `build`. Повтор того же дня не меняет байты слепка. `edits.json` build не переписывает. Чужой `ruleHash` по-прежнему останавливает запись слепка.

## fixture

`--source` — файл, уже прошедший `canonical.schema.json`. Коннектор возвращает его как есть. Слепок совпадает с прямым `build` этого файла и с записанными числами `fixtures/m1`.

## file

`--source` — каталог. Коннектор не знает правки, слепки и формулы. Наружу выходит только bundle.

| Файл | Что это |
| --- | --- |
| `meta.json` | `bundleId`, `asOf`, `sourceWatermark` |
| `search.json` | ответ поиска Jira: `issues[]` с `fields` |
| `changelogs.json` | объект `id → { histories }` |
| `sprints.json` | массив agile-спринтов или `{ "values": [...] }` |

Время приводится к UTC `YYYY-MM-DDTHH:MM:SSZ`. Дата спринта берётся в той зоне, которая записана в файле. Server читает `assignee.name`, Cloud — только `assignee.accountId`. Оценка берётся из `sources.jira.fields.storyPoints`. `storyPointsAtAdd` — значение на самый ранний `addedAt`; если журнал оценки пуст, это текущее число. Поле эпика резолвится в id задачи того же поиска. Связь `outwardIssue` идёт от текущей задачи, `inwardIssue` — к ней. Состав спринта читается из журнала поля `Sprint`: id, а если поле id пустое — имя спринта.

Проверка: `fixtures/m4/file-sprint/expected.canonical.json`. Это разбор выгрузки по правилам выше. `collect` обязан совпасть с ним. Build этого файла и build результата collect дают один и тот же слепок.

## live

`sources.mode: live` возвращает ошибку и файл bundle не создаёт. HTTP в каталоге `connectors` нет. Записанный ответ Jira и контейнер — M5.

## Что сознательно не делается

React, Docker, токен на нелокальный адрес, инкремент `timings` в manifest, Confluence, мессенджер, GitLab.
