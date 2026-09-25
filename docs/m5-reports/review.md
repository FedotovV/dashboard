# M5. Проверка

Команды: `python3 -m pytest` (135 тестов) и `python3 scripts/check_contracts.py` (`contracts ok`). Браузер не поднимался. Ответы экрана читались через `urllib` с `127.0.0.1`. Наружу, в чужую Jira, запросов не было: записанные тела отдавал подставной транспорт, сокет проверялся локальным сервером на `127.0.0.1`.

Сошлось:

- живой разбор `fixtures/m4/file-sprint` совпал с fileimport по `asOf`, задачам, статусам, составу, спринтам и связям;
- `GET /api/sprint`: `E-1.closedBeforeDue = true`, `N-1 = false`, `D-1.storyPoints = 8`, `R-1.scope = removed`, `burndown.params.storyPointsAtAdd = 8`;
- manifest запечатал `d-1`, `e-1`, `n-1`; повторный прогон не сменил байты слепка и байты `timings`; задача вне `terminal` из печати ушла;
- у короткой истории `due-midnight` флаг `changelogComplete` ложный;
- Cloud, пустой токен и редирект на другой хост сеть к чужому адресу не открывают;
- локальный сервер получил `Authorization: Bearer …`, токена нет в bundle, слепке и manifest;
- `Dockerfile` не содержит секрет. Сборку образа здесь запустить нельзя: демона Docker нет.
