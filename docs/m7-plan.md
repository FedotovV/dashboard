# M7. Compose и токен записи

M6 влит: мастер пишет тот же `team.yaml` на localhost. Этот шаг открывает нелокальный bind только вместе с токеном на запись и кладёт один процесс в Compose. Формулы не меняются.

## Статус

- [x] План
- [x] `127.0.0.1` по-прежнему пишет без токена
- [x] Другой адрес без токена не слушает, код 2, до collect
- [x] `PUT` и `POST` правок и настройки сверяют `Authorization: Bearer` или поле формы `token`
- [x] Неверный токен, query и схема `Basic` файл не меняют. Ответ значение не повторяет
- [x] `GET` токен не требует
- [x] `compose.yaml`: секрет снаружи, публикация порта на `127.0.0.1` хоста, внутри `0.0.0.0`

Отчёт: [m7-reports/review.md](m7-reports/review.md).

## Команда

Имя переменной, не само значение:

```bash
export DASHBOARD_TOKEN=...
python3 -m dashboard serve \
  --snapshots var/snapshots \
  --team card \
  --config path/to/team.yaml \
  --edits var/edits.json \
  --host 0.0.0.0 \
  --token-env DASHBOARD_TOKEN
```

Пустая переменная равна отсутствию токена: процесс не начинает слушать. На `127.0.0.1` флаг можно не передавать. Переданный токен на localhost запись не запирает: так форма в браузере на своей машине остаётся прежней.

Токен принимается заголовком `Authorization: Bearer` или полем формы `token`. Поле показывается пустым, только когда bind не локальный. В query токен не читается. Сравнение не отдаёт длину наружу. Значение не пишется в `edits.json`, `team.yaml`, слепок и текст ошибки.

## Compose

```bash
export DASHBOARD_TOKEN=...
export DASHBOARD_TEAM=card
export DASHBOARD_CONFIG=$PWD/path/to/team.yaml
export JIRA_TOKEN=...   # только для live-сбора
docker compose up --build
```

Порт на хосте — `127.0.0.1:8765`. Внутри контейнера адрес `0.0.0.0`, поэтому запись требует `DASHBOARD_TOKEN`. Кто публикует порт шире, меняет строку `ports`; токен уже стоит. `team.yaml` монтируется только на чтение. Каталог данных — `DASHBOARD_DATA` или `./var`: слепки, `edits.json`, `manifest.json`. `JIRA_TOKEN` приходит из окружения хоста и в образ не копируется.

Разовый сбор тем же образом:

```bash
docker compose run --rm --no-deps dashboard \
  run --team /config/team.yaml --source live \
  --out /data/snapshots --manifest /data/manifest.json \
  --edits /data/edits.json
```

## Что не делается

SSO, токен на `GET`, вторая команда, кнопка пересборки, React, живой Cloud.
