# M5. Один Jira

M4 влит: `fixture` и `file` уже собирают bundle. Этот шаг добавляет живой сбор Jira Server / Data Center, печать manifest и один контейнер. Формулы не меняются.

## Статус

- [x] План
- [x] Общий разбор тел search, changelog и sprint для `file` и `live`
- [x] Клиент Server: спринт, поиск по `sprintId`, журнал каждой задачи, страницы до конца
- [x] Чужой хост и редирект наружу не следуют. Тело ошибки и не-200 наружу не попадают
- [x] Токен только из `authEnv`. Нет переменной — код 2, bundle не пишется
- [x] Инкремент manifest: `terminal` запечатывается, выход из `terminal` снимает печать
- [x] `--accept-recompute` по-прежнему пишет новый хеш и пустой `timings`
- [x] Один `Dockerfile`, секрет снаружи, `serve` только на `127.0.0.1`
- [x] Записанный ответ и fileimport дают одни строки `GET /api/sprint`

Отчёт: [m5-reports/review.md](m5-reports/review.md).

## Команда

В `team.yaml` стоит `sources.mode: live`, `sources.jira.deployment: server`, `baseUrl`, `sprintId` и имя переменной `authEnv`.

```bash
export JIRA_TOKEN=...
python3 -m dashboard run \
  --team fixtures/m5/server/team.yaml \
  --source live \
  --manifest var/manifest.json \
  --out var/snapshots
```

`--source` в режиме live не читается. Часы сбора в тесте подменяются. Повтор того же дня не меняет байты слепка. Второй прогон тех же тел не меняет байты `timings`.

Живой Cloud не начинается: для Basic не хватает почты, а в схеме одно имя секрета. Разбор `accountId` в файловой выгрузке остаётся.

## Что совпадает с fileimport

Клиент кладёт ответ поиска, журналы и карточку спринта в ту же функцию, что каталог `fixtures/m4/file-sprint/raw`. Совпадают `asOf` (при тех же часах), задачи, статусы, состав, спринты и связи. `bundleId` и `sourceWatermark` у live свои: `live-{sprintId}` и `live:` плюс хеш тел. Из-за водяного знака хеш bundle в слепке другой. Строки задач и `burndown.params.storyPointsAtAdd` те же: у выгрузки это 8.

## Manifest

После успешного build, если передан `--manifest` и хеш правил совпал, файл получает `timings` текущих задач в роли `terminal`. В строке только `issueId`, `terminal`, `formulaVersion`, `ruleHash`, `changelogComplete`. Секунд и чисел метрик нет. `changelogComplete` — истина, когда первый интервал статуса начинается в `created`. Задача, которая была запечатана, а теперь не в `terminal`, из списка уходит. Чужой `ruleHash` по-прежнему код 3, байты manifest не меняются. `--accept-recompute` записывает новый хеш и пустой список.

## Контейнер

`Dockerfile` ставит PyYAML и jsonschema, копирует `src` и `schema`. Токена и `.env` в образе нет. Процесс внутри — `python -m dashboard`. Каталог слепков, `team.yaml` и переменная секрета монтируются снаружи.

## Что не делается

Живой Cloud, Confluence, мессенджер, GitLab, Compose, планировщик, OIDC, отдельная база, кнопка пересборки, токен на нелокальный `PUT`, React.
